import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { loadDashboardSource } from '../dashboardApi';
import { response } from './fixtures';

beforeEach(() => { sessionStorage.clear(); vi.stubGlobal('fetch', vi.fn(async () => response([]))); });
afterEach(() => vi.unstubAllGlobals());
test.each([
  ['planchas', '/api/inventory/planchas', {}], ['retazos', '/api/inventory/retazos', {}],
  ['clients', '/api/clients', {}],
  ['pendingOrders', '/api/orders', { page: '1', limit: '1', estado: 'PENDIENTE' }],
  ['inProgressOrders', '/api/orders', { page: '1', limit: '1', estado: 'EN_OPTIMIZACION' }],
  ['recentOrders', '/api/orders', { page: '1', limit: '5' }],
])('%s reutiliza GET real con filtros, token y signal', async (source, path, params) => {
  const controller = new AbortController();
  await loadDashboardSource(source, { token: 'synthetic-token', signal: controller.signal });
  expect(fetch).toHaveBeenCalledOnce();
  const [url, options] = fetch.mock.calls[0];
  expect(new URL(url).pathname).toBe(path);
  expect(Object.fromEntries(new URL(url).searchParams)).toEqual(params);
  expect(options).toMatchObject({ method: 'GET', signal: controller.signal, headers: { Authorization: 'Bearer synthetic-token' } });
  expect(options.body).toBeUndefined();
});
test('listado de clientes conserva HTTP status sin exponer detalles internos', async () => {
  fetch.mockResolvedValue(response({ detail: 'SQL internal' }, 401));
  await expect(loadDashboardSource('clients')).rejects.toMatchObject({ status: 401, message: 'Tu sesión ha expirado. Vuelve a iniciar sesión.' });
});
test.each(['planchas', 'retazos', 'clients'])('%s propaga abort como cancelación', async source => {
  fetch.mockRejectedValue(new DOMException('Cancelled', 'AbortError'));
  await expect(loadDashboardSource(source)).rejects.toMatchObject({ name: 'AbortError' });
});
test('fuente desconocida no inventa un endpoint', async () => {
  await expect(loadDashboardSource('unknown')).rejects.toThrow('La respuesta recibida no es válida');
  expect(fetch).not.toHaveBeenCalled();
});
test('GET Inventory conserva token de sesión cuando no hay opciones nuevas', async () => {
  sessionStorage.setItem('optimizador.auth', JSON.stringify({ access_token: 'synthetic-stored', usuario: { rol: 'Operario' } }));
  await loadDashboardSource('planchas');
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer synthetic-stored');
});
