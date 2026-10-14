import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';
import { DashboardPage } from '../DashboardPage';
import { loadDashboardSource } from '../dashboardApi';
import { NavigationContext } from '../../../shared/components/NavigationContext';
import { dashboardUser, deferred, emptyResponse, orderItem, orderPage, sourceResponse } from './fixtures';

vi.mock('../dashboardApi', () => ({ loadDashboardSource: vi.fn() }));
const onNavigate = vi.fn();
function renderPage(role = 'Operario', navigation = {}) {
  return render(<NavigationContext.Provider value={{ onNavigate, availableViews: ['dashboard', 'inventory', 'orders', 'users'], ...navigation }}>
    <DashboardPage user={dashboardUser(role)} token="synthetic" />
  </NavigationContext.Provider>);
}
const section = name => screen.getByRole('region', { name, exact: true });
const metric = (region, label) => within(region).getByText(label, { exact: true }).nextElementSibling;
async function ready() { await waitFor(() => expect(screen.getByRole('button', { name: 'Actualizar datos' })).toBeEnabled()); }
beforeEach(() => { onNavigate.mockClear(); loadDashboardSource.mockReset().mockImplementation(async source => sourceResponse(source)); });

test('presenta unidades/registros reales de inventario y totales paginados con etiquetas precisas', async () => {
  renderPage(); await ready();
  expect(screen.getByRole('heading', { level: 1, name: 'Inicio' })).toBeVisible();
  expect(metric(section('Planchas'), 'Unidades registradas activas')).toHaveTextContent(/^5$/);
  expect(metric(section('Planchas'), 'Registros activos con unidades')).toHaveTextContent(/^1$/);
  expect(metric(section('Planchas'), 'Registros totales')).toHaveTextContent(/^3$/);
  expect(metric(section('Retazos'), 'Retazos activos registrados')).toHaveTextContent(/^1$/);
  expect(metric(section('Pedidos pendientes'), 'Total de pedidos pendientes')).toHaveTextContent(/^23$/);
  expect(metric(section('Pedidos en optimización'), 'Total de pedidos en optimización')).toHaveTextContent(/^7$/);
  expect(metric(section('Clientes registrados'), 'Clientes activos registrados')).toHaveTextContent(/^1$/);
  expect(metric(section('Clientes registrados'), 'Registros totales')).toHaveTextContent(/^2$/);
  expect(screen.queryByText('TEST-ONLY')).not.toBeInTheDocument();
  expect(screen.queryByText('not-real')).not.toBeInTheDocument();
  expect(screen.queryByText('Planchas disponibles')).not.toBeInTheDocument();
});
test.each(['Administrador', 'Almacenero', 'Operario'])('%s recibe únicamente resúmenes y accesos permitidos', async role => {
  renderPage(role); await ready();
  const shortcuts = section('Accesos rápidos');
  expect(within(shortcuts).getByRole('button', { name: 'Abrir Gestión de inventario' })).toBeEnabled();
  expect(within(shortcuts).queryByRole('button', { name: 'Abrir Registro de pedidos' }) !== null).toBe(role !== 'Almacenero');
  expect(within(shortcuts).queryByRole('button', { name: 'Abrir Panel de roles' }) !== null).toBe(role === 'Administrador');
  expect(screen.queryByRole('region', { name: 'Clientes registrados', exact: true }) !== null).toBe(role !== 'Almacenero');
  expect(screen.queryByRole('region', { name: 'Pedidos pendientes', exact: true }) !== null).toBe(role !== 'Almacenero');
  if (role === 'Almacenero') expect(loadDashboardSource.mock.calls.map(([source]) => source)).toEqual(['planchas', 'retazos']);
  expect(within(shortcuts).queryByRole('button', { name: /Optimizaci|Clientes/ })).not.toBeInTheDocument();
});
test('listado conserva orden backend, estado textual, cliente y fecha reales sin afirmar recenticidad global', async () => {
  const items = [orderItem, { ...orderItem, id_pedido: 90, estado: 'CANCELADO', fecha_registro: '2026-10-14T12:00:00Z' }];
  loadDashboardSource.mockImplementation(async source => source === 'recentOrders' ? { ...orderPage, items } : sourceResponse(source));
  renderPage(); await ready();
  const region = section('Pedidos en orden de gestión');
  expect(within(region).getByText(/No cancelados primero; fecha e ID descendentes/)).toBeVisible();
  expect(within(region).getByText(/Mostrando 2 de 23 pedidos/)).toBeVisible();
  const rows = within(region).getAllByRole('listitem');
  expect(within(rows[0]).getByRole('heading', { name: 'Pedido #42' })).toBeVisible();
  expect(within(rows[1]).getByRole('heading', { name: 'Pedido #90' })).toBeVisible();
  expect(within(rows[0]).getByText('Pendiente')).toBeVisible();
  expect(within(rows[1]).getByText('Cancelado')).toBeVisible();
  expect(rows[0].querySelector('time')).toHaveAttribute('datetime', orderItem.fecha_registro);
  expect(within(rows[0]).getByText(orderItem.cliente)).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'Pedidos recientes' })).not.toBeInTheDocument();
});
test('loading muestra feedback por fuente y ningún número provisional', () => {
  loadDashboardSource.mockImplementation(() => new Promise(() => {}));
  renderPage();
  expect(within(section('Planchas')).getByRole('status')).toHaveTextContent('Cargando planchas');
  expect(screen.getByRole('button', { name: 'Actualizar datos' })).toBeDisabled();
  expect(document.querySelectorAll('.dashboard-metrics dd')).toHaveLength(0);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(within(section('Accesos rápidos')).getByRole('button', { name: 'Abrir Registro de pedidos' })).toBeEnabled();
});
test('una fuente lenta no bloquea datos recibidos ni accesos rápidos', async () => {
  const slow = deferred();
  loadDashboardSource.mockImplementation(source => source === 'planchas' ? slow.promise : Promise.resolve(sourceResponse(source)));
  renderPage();
  await waitFor(() => expect(metric(section('Retazos'), 'Retazos activos registrados')).toHaveTextContent('1'));
  expect(within(section('Planchas')).getByRole('status')).toHaveTextContent('Cargando');
  await userEvent.click(within(section('Accesos rápidos')).getByRole('button', { name: 'Abrir Registro de pedidos' }));
  expect(onNavigate).toHaveBeenCalledWith('orders');
  await act(async () => slow.resolve(sourceResponse('planchas')));
  await ready();
});
test('respuestas vacías muestran textos específicos y no errores ni contadores de fallback', async () => {
  loadDashboardSource.mockImplementation(async source => emptyResponse(source));
  renderPage(); await ready();
  for (const text of ['No hay planchas registradas.', 'No hay retazos registrados.', 'No hay pedidos pendientes.', 'No hay pedidos en optimización.', 'No hay clientes registrados.', 'Esta página no contiene pedidos.']) {
    expect(screen.getByText(text)).toBeVisible();
  }
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(document.querySelectorAll('.dashboard-metrics dd')).toHaveLength(0);
});
test('cero activos con registros reales se muestra como dato válido, sin inventar un vacío del endpoint', async () => {
  loadDashboardSource.mockImplementation(async source => source === 'planchas' ? [{ id_plancha: 1, estado: false, cantidad: 9 }] : sourceResponse(source));
  renderPage(); await ready();
  expect(metric(section('Planchas'), 'Unidades registradas activas')).toHaveTextContent(/^0$/);
  expect(metric(section('Planchas'), 'Registros totales')).toHaveTextContent(/^1$/);
  expect(screen.queryByText('No hay planchas registradas.')).not.toBeInTheDocument();
});
test('error total informa y conserva navegación sin presentar datos ni vacío ficticio', async () => {
  loadDashboardSource.mockRejectedValue(new Error('SQL private details'));
  renderPage();
  expect(await screen.findByRole('alert')).toHaveTextContent('Información no disponible');
  expect(screen.getByRole('button', { name: 'Reintentar carga' })).toBeEnabled();
  expect(screen.queryByRole('region', { name: 'Resumen operativo' })).not.toBeInTheDocument();
  expect(screen.queryByText(/SQL private/)).not.toBeInTheDocument();
  expect(within(section('Accesos rápidos')).getByRole('button', { name: 'Abrir Gestión de inventario' })).toBeEnabled();
});
test.each(['planchas', 'recentOrders'])('fallo parcial de %s identifica el bloque y conserva las fuentes válidas', async failed => {
  loadDashboardSource.mockImplementation(async source => { if (source === failed) throw new Error('private'); return sourceResponse(source); });
  renderPage();
  await screen.findByText('Información parcial');
  const failedSection = section(failed === 'planchas' ? 'Planchas' : 'Pedidos en orden de gestión');
  expect(within(failedSection).getByRole('alert')).toHaveTextContent('No se pudo cargar');
  expect(metric(section('Clientes registrados'), 'Clientes activos registrados')).toHaveTextContent('1');
  expect(metric(section('Retazos'), 'Retazos activos registrados')).toHaveTextContent('1');
  expect(failedSection.querySelector('dd')).toBeNull();
  expect(screen.queryByText('private')).not.toBeInTheDocument();
});
test('retry reutiliza el hook, no duplica solicitudes y reemplaza el error por datos', async () => {
  loadDashboardSource.mockRejectedValue(new Error('network'));
  const user = userEvent.setup(); renderPage();
  await screen.findByRole('button', { name: 'Reintentar carga' });
  expect(loadDashboardSource).toHaveBeenCalledTimes(6);
  loadDashboardSource.mockImplementation(async source => sourceResponse(source));
  await user.click(screen.getByRole('button', { name: 'Reintentar carga' }));
  await ready();
  expect(loadDashboardSource).toHaveBeenCalledTimes(12);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(metric(section('Planchas'), 'Unidades registradas activas')).toHaveTextContent('5');
});
test('403 de clientes conserva resúmenes autorizados sin mostrar cifras del bloque rechazado', async () => {
  loadDashboardSource.mockImplementation(async source => { if (source === 'clients') throw Object.assign(new Error('private'), { status: 403 }); return sourceResponse(source); });
  renderPage();
  await screen.findByText('Información parcial');
  expect(within(section('Clientes registrados')).getByRole('alert')).toHaveTextContent('No tienes permiso');
  expect(section('Clientes registrados').querySelector('dd')).toBeNull();
  expect(metric(section('Planchas'), 'Unidades registradas activas')).toHaveTextContent('5');
});
test('accesos rápidos usan botones, Tab, Enter y Space con IDs existentes', async () => {
  const user = userEvent.setup(); renderPage(); await ready();
  const buttons = within(section('Accesos rápidos')).getAllByRole('button');
  buttons[0].focus(); expect(buttons[0]).toHaveFocus();
  await user.keyboard('{Enter}'); expect(onNavigate).toHaveBeenLastCalledWith('inventory');
  await user.tab(); expect(buttons[1]).toHaveFocus();
  await user.keyboard(' '); expect(onNavigate).toHaveBeenLastCalledWith('orders');
  expect(buttons.every(button => button.type === 'button' && button.getAttribute('aria-label')?.startsWith('Abrir '))).toBe(true);
  expect(within(section('Accesos rápidos')).getAllByRole('button').every(button => button.querySelector('svg').getAttribute('aria-hidden') === 'true')).toBe(true);
});
test('no ofrece accesos sin navegación disponible o hacia vistas no montadas', async () => {
  const view = renderPage('Operario', { availableViews: ['dashboard', 'inventory'] }); await ready();
  expect(within(section('Accesos rápidos')).queryByRole('button', { name: 'Abrir Registro de pedidos' })).not.toBeInTheDocument();
  view.unmount(); renderPage('Operario', { onNavigate: null }); await ready();
  expect(screen.queryByRole('region', { name: 'Accesos rápidos' })).not.toBeInTheDocument();
});
test('rol sin acceso no monta workspace ni consulta fuentes', () => {
  renderPage('Unknown');
  expect(screen.getByRole('alert')).toHaveTextContent('No tienes acceso a Inicio');
  expect(loadDashboardSource).not.toHaveBeenCalled();
});
