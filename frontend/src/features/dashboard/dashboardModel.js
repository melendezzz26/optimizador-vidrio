import { canManageOrders, canViewAdministration, canViewDashboard, canViewInventory } from '../authentication/permissions';

export const DASHBOARD_SOURCES = {
  planchas: 'Planchas',
  retazos: 'Retazos',
  pendingOrders: 'Pedidos pendientes',
  inProgressOrders: 'Pedidos en optimización',
  recentOrders: 'Pedidos en orden de gestión',
  clients: 'Clientes registrados',
};
export const ORDER_DESCRIPTION = 'No cancelados primero; fecha e ID descendentes.';
const ORDER_STATES = ['PENDIENTE', 'EN_OPTIMIZACION', 'OPTIMIZADO', 'CONFIRMADO', 'CANCELADO'];

export class DashboardDataError extends Error {
  constructor() { super('La respuesta recibida no es válida. Actualiza los datos.'); }
}

export function getDashboardSources(user) {
  if (!canViewDashboard(user)) return [];
  return [
    ...(canViewInventory(user) ? ['planchas', 'retazos'] : []),
    ...(canManageOrders(user) ? ['pendingOrders', 'inProgressOrders', 'recentOrders', 'clients'] : []),
  ];
}

export function getDashboardActions(user) {
  if (!canViewDashboard(user)) return [];
  return [
    ...(canViewInventory(user) ? [{ view: 'inventory', label: 'Gestión de inventario' }] : []),
    ...(canManageOrders(user) ? [{ view: 'orders', label: 'Registro de pedidos' }] : []),
    ...(canViewAdministration(user) ? [{ view: 'users', label: 'Administración' }] : []),
  ];
}

export function createDashboardBlocks(user) {
  return Object.fromEntries(getDashboardSources(user).map(source => [source, { status: 'loading', data: null, error: '' }]));
}

const isCount = value => Number.isSafeInteger(value) && value >= 0;
const isId = value => Number.isSafeInteger(value) && value > 0;
function records(value, idField) {
  if (!Array.isArray(value) || value.some(item => !item || !isId(item[idField]) || typeof item.estado !== 'boolean')) {
    throw new DashboardDataError();
  }
  return value;
}

export function transformDashboardSource(source, response) {
  if (source === 'planchas') {
    const items = records(response, 'id_plancha');
    if (items.some(item => !isCount(item.cantidad))) throw new DashboardDataError();
    const active = items.filter(item => item.estado && item.cantidad > 0);
    const activeUnits = active.reduce((sum, item) => sum + item.cantidad, 0);
    if (!isCount(activeUnits)) throw new DashboardDataError();
    return { totalRecords: items.length, activeRecords: active.length, activeUnits };
  }
  if (source === 'retazos' || source === 'clients') {
    const items = records(response, source === 'retazos' ? 'id_retazo' : 'id_cliente');
    return { totalRecords: items.length, activeRecords: items.filter(item => item.estado).length };
  }
  if (!response || !Array.isArray(response.items) || !isCount(response.total) || response.items.length > response.total) {
    throw new DashboardDataError();
  }
  if (source === 'pendingOrders' || source === 'inProgressOrders') return { total: response.total };
  if (source !== 'recentOrders' || !isId(response.page) || !isId(response.limit)) throw new DashboardDataError();
  const items = response.items.map(item => {
    if (!item || !isId(item.id_pedido) || !ORDER_STATES.includes(item.estado)
      || typeof item.fecha_registro !== 'string' || !Number.isFinite(Date.parse(item.fecha_registro))
      || typeof item.cliente !== 'string') throw new DashboardDataError();
    return { id: item.id_pedido, registeredAt: item.fecha_registro, state: item.estado, client: item.cliente };
  });
  return { items, total: response.total, page: response.page, limit: response.limit, orderDescription: ORDER_DESCRIPTION };
}

export function isDashboardSourceEmpty(source, data) {
  if (source === 'recentOrders') return data.items.length === 0;
  return (data.totalRecords ?? data.total) === 0;
}

export function getDashboardStatus(blocks) {
  const statuses = Object.values(blocks).map(block => block.status);
  if (!statuses.length) return 'unavailable';
  const errors = statuses.filter(status => status === 'error').length;
  const ready = statuses.filter(status => status === 'success' || status === 'empty').length;
  if (errors && ready) return 'partial-error';
  if (statuses.includes('loading')) return 'loading';
  if (errors === statuses.length) return 'error';
  return statuses.every(status => status === 'empty') ? 'empty' : 'success';
}
