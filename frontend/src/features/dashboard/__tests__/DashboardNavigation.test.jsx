import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import App from '../../../App';
import { dashboardUser, deferred, orderPage, planchas, retazos, clients, response } from './fixtures';

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }));
let actor;
function apiResponse(url) {
  const path = new URL(url).pathname;
  if (path === '/api/auth/login') return response({ access_token: 'synthetic-session', token_type: 'bearer', usuario: actor });
  if (path === '/api/auth/me') return response(actor);
  if (path === '/api/inventory/planchas') return response(planchas.slice(0, 1));
  if (path === '/api/inventory/retazos') return response(retazos);
  if (path === '/api/inventory/tipos-vidrio') return response([]);
  if (path === '/api/clients') return response(clients);
  if (path === '/api/orders') return response(orderPage);
  if (path === '/api/users' || path === '/api/users/roles') return response([]);
  throw new Error('Unexpected test request');
}
const storeSession = () => sessionStorage.setItem('optimizador.auth', JSON.stringify({ access_token: 'synthetic-session', usuario: actor }));
async function login(user) {
  await user.type(screen.getByLabelText('Usuario', { exact: true }), 'O70000001');
  await user.type(screen.getByLabelText('Contraseña', { exact: true }), 'synthetic-only');
  await user.click(screen.getByRole('button', { name: 'Ingresar', exact: true }));
  await screen.findByRole('heading', { name: 'Inicio', exact: true });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Actualizar datos' })).toBeEnabled());
}
beforeEach(() => {
  actor = dashboardUser();
  sessionStorage.clear();
  vi.stubGlobal('fetch', vi.fn(async url => apiResponse(url)));
});
afterEach(() => { sessionStorage.clear(); vi.unstubAllGlobals(); window.history.replaceState({}, '', '/'); });

test('sin sesión no monta Dashboard ni consulta datos protegidos', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Inicio', exact: true })).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});
test.each(['Administrador', 'Almacenero', 'Operario'])('login real de componentes dirige a %s a Inicio y respeta fuentes', async role => {
  actor = dashboardUser(role);
  const user = userEvent.setup();
  render(<App />);
  await login(user);
  expect(screen.queryByRole('heading', { name: 'Iniciar sesión' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Inicio', exact: true })).toHaveAttribute('aria-current', 'page');
  expect(screen.getByText(role)).toBeVisible();
  const paths = fetch.mock.calls.map(([url]) => new URL(url).pathname);
  expect(paths.includes('/api/orders')).toBe(role !== 'Almacenero');
  expect(paths.includes('/api/clients')).toBe(role !== 'Almacenero');
  expect(screen.queryByRole('button', { name: 'Administración', exact: true }) !== null).toBe(role === 'Administrador');
});
test('restaura sesión con me antes de consultar Dashboard y utiliza el rol vigente', async () => {
  actor = dashboardUser('Administrador'); storeSession();
  actor = dashboardUser('Almacenero');
  const restored = deferred();
  fetch.mockImplementationOnce(() => restored.promise);
  render(<App />);
  expect(screen.getByRole('status')).toHaveTextContent('Comprobando la sesión');
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole('heading', { name: 'Inicio' })).not.toBeInTheDocument();
  await act(async () => restored.resolve(response(actor)));
  await screen.findByRole('heading', { name: 'Inicio' });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Actualizar datos' })).toBeEnabled());
  expect(fetch.mock.calls.some(([url]) => new URL(url).pathname === '/api/orders')).toBe(false);
  expect(JSON.parse(sessionStorage.getItem('optimizador.auth')).usuario.rol).toBe('Almacenero');
});
test('Inicio navega por teclado y conserva subpath; logout/relogin vuelve a Inicio desde otro módulo', async () => {
  storeSession(); window.history.replaceState({}, '', '/optimizador-vidrio/');
  const user = userEvent.setup(); render(<App />);
  await screen.findByRole('heading', { name: 'Inicio' });
  await user.click(screen.getByRole('button', { name: 'Registro de pedidos', exact: true }));
  expect(screen.getByRole('button', { name: 'Registro de pedidos', exact: true })).toHaveAttribute('aria-current', 'page');
  screen.getByRole('button', { name: 'Inicio', exact: true }).focus();
  await user.keyboard('{Enter}');
  expect(screen.getByRole('heading', { name: 'Inicio' })).toBeVisible();
  expect(window.location.pathname).toBe('/optimizador-vidrio/');
  await user.click(screen.getByRole('button', { name: 'Registro de pedidos', exact: true }));
  await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
  expect(sessionStorage.getItem('optimizador.auth')).toBeNull();
  expect(screen.queryByRole('heading', { name: 'Inicio' })).not.toBeInTheDocument();
  await login(user);
  expect(screen.getByRole('button', { name: 'Inicio', exact: true })).toHaveAttribute('aria-current', 'page');
});
test('sesión vencida al refresh vuelve a Login sin consultar Dashboard', async () => {
  storeSession(); fetch.mockResolvedValueOnce(response({ detail: 'Sesión vencida' }, 401));
  render(<App />);
  await screen.findByRole('heading', { name: 'Iniciar sesión' });
  expect(sessionStorage.getItem('optimizador.auth')).toBeNull();
  expect(fetch).toHaveBeenCalledTimes(1);
});
test('401 de datos usa logout global y retira el Dashboard', async () => {
  storeSession();
  fetch.mockImplementation(async url => new URL(url).pathname === '/api/inventory/planchas'
    ? response({}, 401) : apiResponse(url));
  render(<App />);
  await screen.findByRole('heading', { name: 'Iniciar sesión' });
  expect(sessionStorage.getItem('optimizador.auth')).toBeNull();
  expect(screen.queryByRole('heading', { name: 'Inicio' })).not.toBeInTheDocument();
});

test.each([
  ['Gestión de inventario', 'Gestión de inventario'],
  ['Registro de pedidos', 'Registro de pedidos'],
  ['Optimización', 'Optimización'],
  ['Administración', 'Administración'],
])('acceso rápido %s navega al módulo real desde App', async (quickLabel, sidebarLabel) => {
  actor = dashboardUser('Administrador'); storeSession();
  const user = userEvent.setup(); render(<App />);
  await screen.findByRole('heading', { name: 'Inicio' });
  await user.click(await screen.findByRole('button', { name: `Abrir ${quickLabel}`, exact: true }));
  expect(screen.getByRole('button', { name: sidebarLabel, exact: true })).toHaveAttribute('aria-current', 'page');
  expect(screen.queryByRole('heading', { name: 'Inicio', exact: true })).not.toBeInTheDocument();
});
