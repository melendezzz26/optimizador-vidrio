import { getPlanchas, getRetazos } from '../inventory/inventoryApi';
import { listClients } from '../clients/clientsApi';
import { listOrders } from '../orders/ordersApi';
import { DashboardDataError } from './dashboardModel';

// Page sizes bound transport/presentation; operational counts always use API total.
const loaders = {
  planchas: options => getPlanchas(options),
  retazos: options => getRetazos(options),
  pendingOrders: options => listOrders({ page: 1, limit: 1, estado: 'PENDIENTE' }, options),
  inProgressOrders: options => listOrders({ page: 1, limit: 1, estado: 'EN_OPTIMIZACION' }, options),
  recentOrders: options => listOrders({ page: 1, limit: 5 }, options),
  clients: options => listClients(options),
};

export async function loadDashboardSource(source, options) {
  if (!Object.hasOwn(loaders, source)) throw new DashboardDataError();
  return loaders[source](options);
}
