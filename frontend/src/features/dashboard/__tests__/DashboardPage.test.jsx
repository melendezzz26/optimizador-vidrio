import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';
import { NavigationContext } from '../../../shared/components/NavigationContext';
import { DashboardPage } from '../DashboardPage';

const state = vi.hoisted(() => ({ loadDashboardData: vi.fn() }));
vi.mock('../dashboardData', async (importOriginal) => ({
  ...await importOriginal(),
  loadDashboardData: state.loadDashboardData,
}));

function makeDashboardData(overrides = {}) {
  return {
    recentOrders: [
      {
        id: 184,
        client: 'Constructora Norte',
        date: '2026-10-13T13:30:00Z',
        status: 'PENDIENTE',
        pieceCount: 4,
        glassSummary: 'Templado 6 mm',
      },
      {
        id: 183,
        client: 'María López',
        date: '2026-10-12T09:15:00Z',
        status: 'CONFIRMADO',
        pieceCount: 2,
        glassSummary: 'Laminado 8 mm',
      },
    ],
    totalOrders: 14,
    pendingOrders: [{ id_pedido: 184 }],
    pendingCount: 1,
    inventory: {
      sheets: [
        { id_plancha: 1, id_tipo_vidrio: 1, cantidad: 8, estado: true },
        { id_plancha: 2, id_tipo_vidrio: 1, cantidad: 4, estado: true },
        { id_plancha: 3, id_tipo_vidrio: 2, cantidad: 20, estado: false },
      ],
      offcuts: [
        { id_retazo: 9, id_tipo_vidrio: 1, estado: true },
        { id_retazo: 10, id_tipo_vidrio: 2, estado: true },
        { id_retazo: 11, id_tipo_vidrio: 2, estado: false },
      ],
      materials: [
        { id_tipo_vidrio: 1, nombre: 'Templado', estado: true },
        { id_tipo_vidrio: 2, nombre: 'Laminado', estado: true },
      ],
      sheetError: null,
      offcutError: null,
      materialsError: null,
    },
    clientsCount: 2,
    recentError: null,
    pendingError: null,
    clientsError: null,
    unauthorized: false,
    recentDetailsPartial: false,
    ...overrides,
  };
}

function renderDashboard(onNavigate = vi.fn(), data = makeDashboardData()) {
  state.loadDashboardData.mockResolvedValue(data);
  return {
    onNavigate,
    ...render(
      <NavigationContext.Provider value={{
        onNavigate,
        availableViews: ['dashboard', 'orders', 'inventory', 'new-order', 'register-plancha', 'register-retazo'],
      }}>
        <DashboardPage
          user={{ nombre: 'Ana Técnica', rol: 'Administrador' }}
          token="dashboard-token"
          canAccessOrders
          canAccessInventory
          canRegisterSheets
          canRegisterOffcuts
        />
      </NavigationContext.Provider>,
    ),
  };
}

beforeEach(() => state.loadDashboardData.mockReset());

test('presenta indicadores derivados de inventario, pedidos y clientes reales', async () => {
  renderDashboard();

  expect(await screen.findByRole('heading', { name: 'Dashboard operativo' })).toBeVisible();
  expect(screen.getByText('Resumen operativo de inventario, pedidos y clientes')).toBeVisible();
  expect(screen.getByText('Ana', { exact: true })).toBeVisible();
  expect(screen.getByLabelText('Planchas disponibles: 12')).toBeVisible();
  expect(screen.getByLabelText('Retazos reutilizables: 2')).toBeVisible();
  expect(screen.getByLabelText('Pedidos pendientes: 1')).toBeVisible();
  expect(screen.getByLabelText('Pedidos registrados: 14')).toBeVisible();
  expect(screen.getByLabelText('Clientes registrados: 2')).toBeVisible();
  expect(screen.getByText('Constructora Norte')).toBeVisible();
  expect(screen.getByText('Templado 6 mm')).toBeVisible();
  expect(screen.getByRole('columnheader', { name: 'Piezas' })).toBeVisible();
  expect(screen.getByText('Templado', { selector: 'strong' })).toBeVisible();
  expect(screen.queryByText('Merma promedio')).not.toBeInTheDocument();
  expect(screen.queryByText(/optimizaci[oó]n M1|M2|demostraci[oó]n/i)).not.toBeInTheDocument();
});

test('navega desde los accesos rápidos y ofrece acciones reales por pedido', async () => {
  const onNavigate = vi.fn();
  const user = userEvent.setup();
  renderDashboard(onNavigate);
  const pendingRow = await screen.findByRole('row', { name: /#184 Constructora Norte/ });

  await user.click(screen.getByRole('button', { name: 'Nuevo pedido' }));
  expect(onNavigate).toHaveBeenCalledWith('new-order');
  await user.click(await screen.findByRole('button', { name: /Registrar plancha/ }));
  expect(onNavigate).toHaveBeenCalledWith('register-plancha');
  await user.click(screen.getByRole('button', { name: /Registrar retazo/ }));
  expect(onNavigate).toHaveBeenCalledWith('register-retazo');
  await user.click(screen.getByRole('button', { name: /^Gestión de inventario Consultar planchas y retazos/ }));
  expect(onNavigate).toHaveBeenCalledWith('inventory');

  await user.click(within(pendingRow).getByRole('button', { name: 'Ver pedido 184' }));
  expect(onNavigate).toHaveBeenCalledWith('orders', { order: { id: 184, mode: 'view' } });
  await user.click(within(pendingRow).getByRole('button', { name: 'Editar pedido 184' }));
  expect(onNavigate).toHaveBeenCalledWith('orders', { order: { id: 184, mode: 'edit' } });
  await user.click(within(pendingRow).getByRole('button', { name: 'Cancelar pedido 184' }));
  expect(onNavigate).toHaveBeenCalledWith('orders', { order: { id: 184, mode: 'cancel' } });

  const confirmedRow = screen.getByRole('row', { name: /#183 María López/ });
  expect(within(confirmedRow).getByRole('button', { name: 'Ver pedido 183' })).toBeVisible();
  expect(within(confirmedRow).queryByRole('button', { name: 'Editar pedido 183' })).not.toBeInTheDocument();
  expect(within(confirmedRow).queryByRole('button', { name: 'Cancelar pedido 183' })).not.toBeInTheDocument();
});

test('muestra estados vacíos cuando todavía no hay pedidos ni existencias', async () => {
  renderDashboard(vi.fn(), makeDashboardData({
    recentOrders: [],
    totalOrders: 0,
    pendingOrders: [],
    pendingCount: 0,
    inventory: {
      sheets: [], offcuts: [], materials: [],
      sheetError: null, offcutError: null, materialsError: null,
    },
    clientsCount: 0,
  }));

  expect(await screen.findByText('No hay pedidos registrados todavía.')).toBeVisible();
  expect(screen.getByText('No hay materiales registrados todavía.')).toBeVisible();
  expect(screen.getByLabelText('Planchas disponibles: 0')).toBeVisible();
  expect(screen.getByLabelText('Pedidos pendientes: 0')).toBeVisible();
});

test('expone errores por fuente y conserva los datos que sí respondieron', async () => {
  renderDashboard(vi.fn(), makeDashboardData({
    pendingCount: null,
    pendingError: new Error('No se pudieron consultar pedidos pendientes.'),
    clientsCount: null,
    clientsError: new Error('No se pudo consultar clientes.'),
    inventory: {
      sheets: null,
      offcuts: [{ id_retazo: 9, id_tipo_vidrio: 1, estado: true }],
      materials: [{ id_tipo_vidrio: 1, nombre: 'Templado', estado: true }],
      sheetError: new Error('No se pudieron consultar planchas.'),
      offcutError: null,
      materialsError: null,
    },
  }));

  expect(await screen.findByRole('alert')).toHaveTextContent('Pedidos pendientes: No se pudieron consultar pedidos pendientes.');
  expect(screen.getByRole('alert')).toHaveTextContent('Clientes: No se pudo consultar clientes.');
  expect(screen.getByText('Planchas: No se pudieron consultar planchas.')).toBeVisible();
  expect(screen.getByText('Constructora Norte')).toBeVisible();
  expect(screen.getByLabelText('Pedidos registrados: 14')).toBeVisible();
  expect(screen.getByLabelText('Pedidos pendientes: —')).toBeVisible();
  expect(screen.getByLabelText('Retazos reutilizables: 1')).toBeVisible();
});

test('indica cuando solo parte del detalle de pedidos está disponible', async () => {
  renderDashboard(vi.fn(), makeDashboardData({ recentDetailsPartial: true }));

  expect(await screen.findByText('Algunos detalles de piezas no están disponibles en este momento.')).toBeVisible();
  expect(screen.getByLabelText('Planchas disponibles: 12')).toBeVisible();
  expect(screen.getByLabelText('Clientes registrados: 2')).toBeVisible();
});
