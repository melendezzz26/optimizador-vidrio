import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import App from '../../App';

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));
vi.mock('../../features/authentication', () => ({
  useSession: () => ({ session: { token: 'synthetic', usuario: { nombre: 'Ana Técnica', rol: 'Administrador' } }, isChecking: false }),
  getAccessToken: () => 'synthetic',
  canManageOrders: () => true,
  canManagePlanchas: () => true,
  canManageRetazos: () => true,
  canExecuteOptimization: () => true,
  canManageUsers: () => false,
  canViewInventory: () => true,
  SessionBar: () => null,
  LoginForm: () => null,
}));

function stubStagingApi() {
  vi.stubGlobal('fetch', vi.fn(async (url) => ({
    ok: true,
    status: 200,
    json: async () => String(url).includes('/api/orders')
      ? { items: [], total: 0, total_pages: 0 }
      : [],
  })));
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState({}, '', '/');
});

test('Pages abre el editor desde Nuevo pedido sin abandonar el subpath', async () => {
  window.history.replaceState({}, '', '/optimizador-vidrio/');
  stubStagingApi();
  const user = userEvent.setup();
  render(<App />);

  const sidebar = screen.getByRole('complementary', { name: 'Módulos de NewGlass' });
  expect(await screen.findByRole('heading', { name: 'Dashboard operativo' })).toBeVisible();
  expect(within(sidebar).getByRole('button', { name: 'Dashboard', exact: true })).toHaveAttribute('aria-current', 'page');
  await user.click(within(sidebar).getByRole('button', { name: 'Nuevo pedido', exact: true }));
  await screen.findByText('No hay piezas agregadas');
  await user.click(screen.getByRole('button', { name: 'Agregar pieza' }));
  await user.selectOptions(screen.getByLabelText('Forma'), 'POLIGONO_CONVEXO');
  expect(screen.getByRole('dialog', { name: 'Dibujar Polígono Convexo' })).toBeVisible();
  expect(window.location.pathname).toBe('/optimizador-vidrio/');
  await user.click(screen.getByRole('button', { name: 'Cerrar editor de polígono' }));
  expect(screen.queryByRole('dialog', { name: 'Dibujar Polígono Convexo' })).not.toBeInTheDocument();
  expect(window.location.pathname).toBe('/optimizador-vidrio/');
});

test('Dashboard y HU-015 comparten navegación; rasterización sigue disponible para el rol autorizado', async () => {
  window.history.replaceState({}, '', '/optimizador-vidrio/');
  stubStagingApi();
  const user = userEvent.setup();
  render(<App />);

  const sidebar = screen.getByRole('complementary', { name: 'Módulos de NewGlass' });
  expect(await screen.findByRole('heading', { name: 'Dashboard operativo' })).toBeVisible();
  expect(within(sidebar).getByRole('button', { name: 'Nuevo pedido', exact: true })).toBeVisible();
  expect(within(sidebar).getByRole('button', { name: 'Optimización', exact: true })).toBeVisible();

  await user.click(within(sidebar).getByRole('button', { name: 'Optimización', exact: true }));
  expect(await screen.findByRole('heading', { name: 'Optimización', exact: true })).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Rasterización' })).toBeVisible();
  expect(within(sidebar).getByRole('button', { name: 'Optimización', exact: true })).toHaveAttribute('aria-current', 'page');
  expect(window.location.pathname).toBe('/optimizador-vidrio/');

  await user.click(within(sidebar).getByRole('button', { name: 'Dashboard', exact: true }));
  expect(await screen.findByRole('heading', { name: 'Dashboard operativo' })).toBeVisible();
  expect(within(sidebar).getByRole('button', { name: 'Dashboard', exact: true })).toHaveAttribute('aria-current', 'page');
});
