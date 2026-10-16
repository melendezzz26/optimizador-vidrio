import { withPermissions } from '../../authentication/__tests__/permissionFixtures';
// Synthetic contract fixtures only; never imported by application code.
export const dashboardUser = (rol = 'Operario') => withPermissions({ id_usuario: 11, username: 'O70000001', nombre: 'Persona de prueba', rol });
export const orderItem = { id_pedido: 42, fecha_registro: '2026-10-14T11:00:00Z', estado: 'PENDIENTE', cliente: 'Cliente sintético' };
export const orderPage = { items: [orderItem], total: 23, page: 1, limit: 5, total_pages: 5 };
export const planchas = [
  { id_plancha: 1, estado: true, cantidad: 5, ancho_mm: '1000', alto_mm: '500', espesor_mm: '6', id_tipo_vidrio: 7, fecha_registro: '2026-10-14T11:00:00Z' },
  { id_plancha: 2, estado: true, cantidad: 0 },
  { id_plancha: 3, estado: false, cantidad: 9 },
];
export const retazos = [{ id_retazo: 1, codigo: 'TEST', estado: true, geometria: { type: 'RECTANGULO', width_mm: 10, height_mm: 10 }, area_mm2: '100', espesor_mm: '6', id_tipo_vidrio: 7, fecha_registro: '2026-10-14T11:00:00Z' }];
export const clients = [{ id_cliente: 1, estado: true, nombre_razon_social: 'Cliente sintético', numero_documento: 'TEST-ONLY', telefono: 'not-real' }, { id_cliente: 2, estado: false }];
export const sourceResponse = source => ({ planchas, retazos, clients, pendingOrders: orderPage, inProgressOrders: { ...orderPage, total: 7 }, recentOrders: orderPage })[source];
export const emptyResponse = source => ['pendingOrders', 'inProgressOrders', 'recentOrders'].includes(source)
  ? { items: [], total: 0, page: 1, limit: 5, total_pages: 0 } : [];
export const response = (data, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => data });
export function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
