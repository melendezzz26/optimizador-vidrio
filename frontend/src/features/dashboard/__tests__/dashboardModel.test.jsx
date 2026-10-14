import { expect, test } from 'vitest';
import {
  createDashboardBlocks, DashboardDataError, getDashboardActions, getDashboardSources,
  getDashboardStatus, isDashboardSourceEmpty, ORDER_DESCRIPTION, transformDashboardSource,
} from '../dashboardModel';
import { clients, dashboardUser, orderItem, orderPage, planchas, retazos } from './fixtures';

test.each(['Administrador', 'Operario', 'Almacenero'])('%s recibe únicamente fuentes y destinos reales permitidos', role => {
  const sources = getDashboardSources(dashboardUser(role));
  const actions = getDashboardActions(dashboardUser(role)).map(action => action.view);
  expect(sources).toEqual(role === 'Almacenero' ? ['planchas', 'retazos']
    : ['planchas', 'retazos', 'pendingOrders', 'inProgressOrders', 'recentOrders', 'clients']);
  expect(actions).toEqual(role === 'Administrador' ? ['inventory', 'orders', 'users']
    : role === 'Operario' ? ['inventory', 'orders'] : ['inventory']);
});
test.each([null, { rol: 'Unknown' }])('sin rol reconocido no hay fuentes ni acciones (%j)', user => {
  expect(getDashboardSources(user)).toEqual([]);
  expect(getDashboardActions(user)).toEqual([]);
});
test('planchas distingue registros, unidades e inactivos/cantidad cero sin mutar datos', () => {
  const original = structuredClone(planchas);
  expect(transformDashboardSource('planchas', planchas)).toEqual({ totalRecords: 3, activeRecords: 1, activeUnits: 5 });
  expect(planchas).toEqual(original);
});
test('retazos unitarios y clientes se proyectan sin conservar datos personales', () => {
  expect(transformDashboardSource('retazos', retazos)).toEqual({ totalRecords: 1, activeRecords: 1 });
  expect(transformDashboardSource('clients', clients)).toEqual({ totalRecords: 2, activeRecords: 1 });
});
test.each(['pendingOrders', 'inProgressOrders'])('%s usa total HTTP y nunca longitud de la página', source => {
  expect(transformDashboardSource(source, orderPage)).toEqual({ total: 23 });
});
test('recientes conserva el orden de gestión recibido y proyecta campos reales', () => {
  const input = { ...orderPage, items: [{ ...orderItem, id_pedido: 2 }, { ...orderItem, id_pedido: 99, estado: 'CANCELADO', debug: 'discard' }] };
  const result = transformDashboardSource('recentOrders', input);
  expect(result.items.map(item => item.id)).toEqual([2, 99]);
  expect(result.items[1]).toEqual({ id: 99, registeredAt: orderItem.fecha_registro, state: 'CANCELADO', client: orderItem.cliente });
  expect(result).toMatchObject({ total: 23, page: 1, limit: 5, orderDescription: ORDER_DESCRIPTION });
});
test.each([
  ['planchas', null], ['planchas', [{ id_plancha: 1, estado: true, cantidad: -1 }]],
  ['retazos', [{ id_retazo: 1, estado: 'true' }]], ['clients', {}],
  ['pendingOrders', { items: [], total: NaN }], ['inProgressOrders', { items: [], total: -1 }],
  ['recentOrders', { ...orderPage, items: [{ ...orderItem, fecha_registro: 'invalid' }] }],
])('%s rechaza respuesta inválida sin fabricar un cero', (source, data) => {
  expect(() => transformDashboardSource(source, data)).toThrow(DashboardDataError);
});
test('loading no tiene datos y empty solo deriva de respuesta válida', () => {
  expect(Object.values(createDashboardBlocks(dashboardUser())).every(block => block.status === 'loading' && block.data === null)).toBe(true);
  const empty = transformDashboardSource('planchas', []);
  expect(empty).toEqual({ totalRecords: 0, activeRecords: 0, activeUnits: 0 });
  expect(isDashboardSourceEmpty('planchas', empty)).toBe(true);
  expect(isDashboardSourceEmpty('planchas', transformDashboardSource('planchas', [{ id_plancha: 1, estado: false, cantidad: 3 }]))).toBe(false);
});
test.each([
  [[], 'unavailable'], [['loading', 'success'], 'loading'], [['empty', 'empty'], 'empty'],
  [['error', 'error'], 'error'], [['error', 'success'], 'partial-error'], [['success', 'empty'], 'success'],
])('estado global de %j distingue carga/vacío/fallo/parcial', (statuses, expected) => {
  expect(getDashboardStatus(Object.fromEntries(statuses.map((status, index) => [index, { status }])))).toBe(expected);
});
