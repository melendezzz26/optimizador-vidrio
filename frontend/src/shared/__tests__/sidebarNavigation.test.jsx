import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import App from '../../App';
import { withPermissions } from '../../features/authentication/__tests__/permissionFixtures';

const state = vi.hoisted(() => ({ role: 'Administrador', signOut: vi.fn() }));
vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));
vi.mock('../../features/authentication', async importOriginal => ({
  ...await importOriginal(),
  useSession: () => ({ session: { token: 'synthetic', usuario: withPermissions({ nombre: 'Ana Técnica', username: 'A12345678', rol: state.role }) }, isChecking: false, signOut: state.signOut }),
}));
beforeEach(() => {
  state.role = 'Administrador'; state.signOut.mockClear();
  vi.stubGlobal('fetch', vi.fn(async url => ({ ok: true, status: 200, json: async () => String(url).endsWith('/api/orders?limit=10&offset=0') || String(url).includes('/api/orders?') ? { items: [], total: 0, total_pages: 0, page: 1, limit: 10 } : [] })));
});
afterEach(() => vi.unstubAllGlobals());

test('módulos accesibles solo desde sidebar; header conserva identidad, rol y cierre de sesión', async () => {
  const user = userEvent.setup(); render(<App />);
  const sidebar = screen.getByRole('complementary', { name: 'Módulos de NewGlass' });
  const header = screen.getByText('Ana Técnica').closest('header');
  expect(within(header).getAllByRole('button')).toHaveLength(1);
  expect(within(header).getByRole('button', { name: 'Cerrar sesión' })).toBeVisible();
  expect(within(header).getByText('Administrador')).toBeVisible();
  expect(within(header).queryByRole('navigation')).not.toBeInTheDocument();
  for (const label of ['Inicio', 'Registro de pedidos', 'Optimización', 'Gestión de inventario', 'Administración']) {
    expect(screen.getAllByRole('button', { name: label, exact: true })).toHaveLength(1);
    expect(within(sidebar).getByRole('button', { name: label, exact: true })).toBeEnabled();
  }
  await user.click(within(sidebar).getByRole('button', { name: 'Gestión de inventario' }));
  expect(screen.getByRole('heading', { name: 'Gestión de Inventario' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Gestión de inventario', exact: true })).toHaveAttribute('aria-current', 'page');
  await user.click(screen.getByRole('button', { name: 'Administración', exact: true }));
  expect(screen.getByRole('button', { name: 'Administración', exact: true })).toHaveAttribute('aria-current', 'page');
  const orders = screen.getByRole('button', { name: 'Registro de pedidos', exact: true });
  orders.focus(); await user.keyboard('{Enter}');
  expect(screen.getByRole('button', { name: 'Registro de pedidos', exact: true })).toHaveAttribute('aria-current', 'page');
  await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
  expect(state.signOut).toHaveBeenCalledOnce();
});

test('sidebar respeta permisos del operario sin exponer Administración', () => {
  state.role = 'Operario'; render(<App />);
  expect(screen.queryByRole('button', { name: 'Administración' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Gestión de inventario', exact: true })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Optimización', exact: true })).toBeVisible();
});

test.each(['Administrador', 'Operario'])('%s navega a Optimization por teclado sin cambiar subpath', async role => {
  state.role = role;
  window.history.replaceState({}, '', '/optimizador-vidrio/');
  const user = userEvent.setup(); render(<App />);
  const button = screen.getByRole('button', { name: 'Optimización', exact: true });
  button.focus(); await user.keyboard('{Enter}');
  expect(screen.getByRole('heading', { name: 'Optimización', exact: true })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Optimización', exact: true })).toHaveAttribute('aria-current', 'page');
  expect(window.location.pathname).toBe('/optimizador-vidrio/');
  expect(screen.getAllByRole('button', { name: 'Cerrar sesión' })).toHaveLength(1);
  window.history.replaceState({}, '', '/');
});

test('Almacenero entra a Inicio y conserva Inventory sin exponer Optimization', () => {
  state.role = 'Almacenero'; render(<App />);
  expect(screen.queryByRole('button', { name: 'Optimización' })).not.toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Inicio' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Gestión de inventario', exact: true })).toBeVisible();
});
