import { beforeEach, expect, test, vi } from 'vitest';
import { loadDashboardData } from '../dashboardData';

const api = vi.hoisted(() => ({
  listClients: vi.fn(),
  getPlanchas: vi.fn(),
  getRetazos: vi.fn(),
  getTiposVidrio: vi.fn(),
  getOrder: vi.fn(),
  listOrders: vi.fn(),
}));

vi.mock('../../clients', () => ({ listClients: api.listClients }));
vi.mock('../../inventory', () => ({
  getPlanchas: api.getPlanchas,
  getRetazos: api.getRetazos,
  getTiposVidrio: api.getTiposVidrio,
}));
vi.mock('../../orders', () => ({ getOrder: api.getOrder, listOrders: api.listOrders }));

beforeEach(() => vi.resetAllMocks());

test('deriva el resumen con respuestas actuales de pedidos, piezas, inventario y clientes', async () => {
  api.listOrders
    .mockResolvedValueOnce({
      items: [{
        id_pedido: 42,
        cliente: 'Cristales del Norte',
        fecha_registro: '2026-10-14T12:00:00Z',
        estado: 'PENDIENTE',
      }],
      total: 7,
    })
    .mockResolvedValueOnce({ items: [{ id_pedido: 42, estado: 'PENDIENTE' }], total: 2 });
  api.getOrder.mockResolvedValue({ piezas: [
    { id_tipo_vidrio: 5, espesor_mm: 6, cantidad: 3 },
    { id_tipo_vidrio: 5, espesor_mm: 6, cantidad: 2 },
  ] });
  api.getPlanchas.mockResolvedValue([{ id_plancha: 10, cantidad: 9, estado: true }]);
  api.getRetazos.mockResolvedValue([{ id_retazo: 12, estado: true }]);
  api.getTiposVidrio.mockResolvedValue([{ id_tipo_vidrio: 5, nombre: 'Templado' }]);
  api.listClients.mockResolvedValue([{ id_cliente: 1 }, { id_cliente: 2 }, { id_cliente: 3 }]);

  const result = await loadDashboardData({ token: 'real-session', canAccessOrders: true, canAccessInventory: true });

  expect(api.listOrders).toHaveBeenNthCalledWith(1, { page: 1, limit: 6 }, { token: 'real-session' });
  expect(api.listOrders).toHaveBeenNthCalledWith(2, { page: 1, limit: 100, estado: 'PENDIENTE' }, { token: 'real-session' });
  expect(result.totalOrders).toBe(7);
  expect(result.pendingCount).toBe(2);
  expect(result.clientsCount).toBe(3);
  expect(result.recentOrders).toEqual([{
    id: 42,
    client: 'Cristales del Norte',
    date: '2026-10-14T12:00:00Z',
    status: 'PENDIENTE',
    pieceCount: 5,
    glassSummary: 'Templado 6 mm',
  }]);
  expect(result.inventory).toEqual({
    sheets: [{ id_plancha: 10, cantidad: 9, estado: true }],
    offcuts: [{ id_retazo: 12, estado: true }],
    materials: [{ id_tipo_vidrio: 5, nombre: 'Templado' }],
    sheetError: null,
    offcutError: null,
    materialsError: null,
  });
  expect(result.recentError).toBeNull();
  expect(result.pendingError).toBeNull();
});

test('mantiene las fuentes disponibles e informa las consultas que fallan', async () => {
  const pendingError = Object.assign(new Error('Sin acceso'), { status: 403 });
  api.listOrders.mockResolvedValueOnce({ items: [], total: 0 }).mockRejectedValueOnce(pendingError);
  api.getOrder.mockClear();
  api.getPlanchas.mockResolvedValue([{ id_plancha: 10, cantidad: 4, estado: true }]);
  api.getRetazos.mockRejectedValue(new Error('Sin conexión'));
  api.getTiposVidrio.mockResolvedValue([]);
  api.listClients.mockResolvedValue([{ id_cliente: 1 }]);

  const result = await loadDashboardData({ canAccessOrders: true, canAccessInventory: true });

  expect(result.totalOrders).toBe(0);
  expect(result.pendingCount).toBeNull();
  expect(result.pendingError).toBe(pendingError);
  expect(result.clientsCount).toBe(1);
  expect(result.inventory.sheets).toEqual([{ id_plancha: 10, cantidad: 4, estado: true }]);
  expect(result.inventory.offcuts).toBeNull();
  expect(result.inventory.offcutError).toBeInstanceOf(Error);
  expect(result.unauthorized).toBe(false);
});
