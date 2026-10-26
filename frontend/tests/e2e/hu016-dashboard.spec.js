import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const evidenceDir = fileURLToPath(new URL('../../../docs/evidence/sprint-02/HU-016/t3/screenshots/', import.meta.url));
mkdirSync(evidenceDir, { recursive: true });

const actors = {
  administrator: {
    id_usuario: 1,
    username: 'A70000003',
    nombre: 'Administrador NewGlass',
    rol: 'Administrador',
    permisos: [
      'users.view', 'users.manage', 'roles.view', 'roles.manage',
      'inventory.view', 'inventory.manage',
      'orders.view', 'orders.create', 'orders.update', 'orders.cancel',
      'optimization.view', 'optimization.execute', 'optimization.confirm',
    ],
  },
  operator: {
    id_usuario: 2,
    username: 'O70000001',
    nombre: 'Operario NewGlass',
    rol: 'Operario',
    permisos: [
      'inventory.view',
      'orders.view', 'orders.create', 'orders.update', 'orders.cancel',
      'optimization.view', 'optimization.execute', 'optimization.confirm',
    ],
  },
  warehouse: {
    id_usuario: 3,
    username: 'A70000002',
    nombre: 'Almacenero NewGlass',
    rol: 'Almacenero',
    permisos: ['inventory.view', 'inventory.manage', 'optimization.view'],
  },
  noFunctions: {
    id_usuario: 4,
    username: 'U70000004',
    nombre: 'Usuario Sin Permisos',
    rol: 'SinFunciones',
    permisos: [],
  },
};

const planchasFixture = [
  { id_plancha: 1, estado: true, cantidad: 5, ancho_mm: '1000', alto_mm: '500', espesor_mm: '6', id_tipo_vidrio: 7, fecha_registro: '2026-10-25T12:00:00Z' },
  { id_plancha: 2, estado: true, cantidad: 0, ancho_mm: '1200', alto_mm: '600', espesor_mm: '6', id_tipo_vidrio: 7, fecha_registro: '2026-10-25T12:00:00Z' },
];

const retazosFixture = [
  { id_retazo: 1, codigo: 'RET-01', estado: true, geometria: { type: 'RECTANGULO', width_mm: 200, height_mm: 150 }, area_mm2: '30000', espesor_mm: '6', id_tipo_vidrio: 7, fecha_registro: '2026-10-25T12:00:00Z' },
];

const clientsFixture = [
  { id_cliente: 41, estado: true, nombre_razon_social: 'Vidrios del Sur', numero_documento: '20123456789' },
  { id_cliente: 42, estado: false, nombre_razon_social: 'Cliente Inactivo', numero_documento: '20987654321' },
];

async function setupApiMock(page, currentActor, options = {}) {
  const intercepted = [];
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();

    if (method === 'POST' && path === '/api/auth/login') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'synthetic-jwt-token-hu016',
          token_type: 'bearer',
          usuario: currentActor,
        }),
      });
    }

    if (method === 'GET' && path === '/api/auth/me') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(currentActor),
      });
    }

    if (options.partialFailPlanchas && path === '/api/inventory/planchas') {
      intercepted.push({ path, status: 503 });
      return route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Error temporal simulado en planchas' }),
      });
    }

    intercepted.push({ path, status: 200 });

    if (path === '/api/inventory/planchas') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(planchasFixture) });
    }
    if (path === '/api/inventory/retazos') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(retazosFixture) });
    }
    if (path === '/api/inventory/tipos-vidrio') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ id_tipo_vidrio: 7, nombre: 'Vidrio Flotado' }]) });
    }
    if (path === '/api/clients') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(clientsFixture) });
    }
    if (path === '/api/orders') {
      const estado = url.searchParams.get('estado');
      if (estado === 'PENDIENTE') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [{ id_pedido: 101, fecha_registro: '2026-10-25T10:00:00Z', estado: 'PENDIENTE', cliente: 'Vidrios del Sur' }],
            total: 12, page: 1, limit: 1, total_pages: 12,
          }),
        });
      }
      if (estado === 'EN_OPTIMIZACION') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [{ id_pedido: 102, fecha_registro: '2026-10-25T11:00:00Z', estado: 'EN_OPTIMIZACION', cliente: 'Cristales Centro' }],
            total: 4, page: 1, limit: 1, total_pages: 4,
          }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            { id_pedido: 101, fecha_registro: '2026-10-25T10:00:00Z', estado: 'PENDIENTE', cliente: 'Vidrios del Sur' },
            { id_pedido: 102, fecha_registro: '2026-10-25T11:00:00Z', estado: 'EN_OPTIMIZACION', cliente: 'Cristales Centro' },
          ],
          total: 16, page: 1, limit: 5, total_pages: 4,
        }),
      });
    }

    if (path.startsWith('/api/users')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }

    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });

  return intercepted;
}

async function loginUser(page, username, password = 'ValidPassword2026!') {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Iniciar sesión' })).toBeVisible();
  await page.getByLabel('Usuario', { exact: true }).fill(username);
  await page.getByLabel('Contraseña', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Inicio', exact: true })).toBeVisible();
}

async function capture(page, filename) {
  await page.screenshot({
    path: `${evidenceDir}/${filename}`,
    fullPage: true,
    animations: 'disabled',
  });
}

test('CA-01, CA-03, CA-04, CA-10: Dashboard real para Administrador con todos los accesos', async ({ page }) => {
  const actor = actors.administrator;
  await setupApiMock(page, actor);
  await loginUser(page, actor.username);

  await expect(page.getByText(`Hola, ${actor.nombre}`)).toBeVisible();
  await expect(page.locator('aside.ng-sidebar').getByRole('button', { name: 'Inicio', exact: true }))
    .toHaveAttribute('aria-current', 'page');

  const shortcuts = page.getByRole('region', { name: 'Accesos rápidos' });
  await expect(shortcuts.getByRole('button', { name: 'Abrir Gestión de inventario' })).toBeVisible();
  await expect(shortcuts.getByRole('button', { name: 'Abrir Registro de pedidos' })).toBeVisible();
  await expect(shortcuts.getByRole('button', { name: 'Abrir Optimización' })).toBeVisible();
  await expect(shortcuts.getByRole('button', { name: 'Abrir Administración' })).toBeVisible();

  await expect(page.getByRole('region', { name: 'Planchas' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Retazos' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Pedidos pendientes' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Pedidos en optimización' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Clientes registrados' })).toBeVisible();

  await capture(page, 'dashboard-administrador.png');
});

test('CA-04, CA-10, CA-12: Dashboard real para Operario sin Administración', async ({ page }) => {
  const actor = actors.operator;
  await setupApiMock(page, actor);
  await loginUser(page, actor.username);

  await expect(page.getByText(`Hola, ${actor.nombre}`)).toBeVisible();
  const shortcuts = page.getByRole('region', { name: 'Accesos rápidos' });
  await expect(shortcuts.getByRole('button', { name: 'Abrir Gestión de inventario' })).toBeVisible();
  await expect(shortcuts.getByRole('button', { name: 'Abrir Registro de pedidos' })).toBeVisible();
  await expect(shortcuts.getByRole('button', { name: 'Abrir Optimización' })).toBeVisible();
  await expect(shortcuts.getByRole('button', { name: 'Abrir Administración' })).toHaveCount(0);

  await capture(page, 'dashboard-operario.png');
});

test('CA-04, CA-10, CA-11: Dashboard real para Almacenero sin Pedidos ni Ejecución', async ({ page }) => {
  const actor = actors.warehouse;
  const requests = await setupApiMock(page, actor);
  await loginUser(page, actor.username);

  await expect(page.getByText(`Hola, ${actor.nombre}`)).toBeVisible();
  const shortcuts = page.getByRole('region', { name: 'Accesos rápidos' });
  await expect(shortcuts.getByRole('button', { name: 'Abrir Gestión de inventario' })).toBeVisible();
  await expect(shortcuts.getByRole('button', { name: 'Abrir Optimización' })).toBeVisible();
  await expect(shortcuts.getByRole('button', { name: 'Abrir Registro de pedidos' })).toHaveCount(0);
  await expect(shortcuts.getByRole('button', { name: 'Abrir Administración' })).toHaveCount(0);

  expect(requests.some(r => r.path === '/api/orders')).toBe(false);
  expect(requests.some(r => r.path === '/api/clients')).toBe(false);

  await capture(page, 'dashboard-almacenero.png');
});

test('CA-03, §4, §12: Sesión sin funciones autorizadas accede a Inicio con mensaje explicativo', async ({ page }) => {
  const actor = actors.noFunctions;
  const requests = await setupApiMock(page, actor);
  await loginUser(page, actor.username);

  await expect(page.getByRole('heading', { level: 1, name: 'Inicio' })).toBeVisible();
  await expect(page.getByText(`Hola, ${actor.nombre}`)).toBeVisible();
  await expect(page.getByText('Sin funciones habilitadas')).toBeVisible();
  await expect(page.getByText(/Tu cuenta no tiene módulos ni fuentes de información/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cerrar sesión' })).toBeVisible();

  expect(requests.filter(r => r.path !== '/api/auth/login' && r.path !== '/api/auth/me')).toHaveLength(0);

  await capture(page, 'dashboard-sin-funciones.png');
});

test('CA-02, CA-10: Navegación de acceso rápido a Optimización y retorno por Sidebar', async ({ page }) => {
  const actor = actors.administrator;
  await setupApiMock(page, actor);
  await loginUser(page, actor.username);

  const shortcuts = page.getByRole('region', { name: 'Accesos rápidos' });
  await shortcuts.getByRole('button', { name: 'Abrir Optimización' }).click();

  await expect(page.locator('aside.ng-sidebar').getByRole('button', { name: 'Optimización', exact: true }))
    .toHaveAttribute('aria-current', 'page');
  await capture(page, 'dashboard-navegacion-optimizacion.png');

  await page.locator('aside.ng-sidebar').getByRole('button', { name: 'Inicio', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Inicio' })).toBeVisible();
  await expect(page.locator('aside.ng-sidebar').getByRole('button', { name: 'Inicio', exact: true }))
    .toHaveAttribute('aria-current', 'page');
});

test('CA-17: Verificación responsive sin overflow en 1440px, 1024px y 800px', async ({ page }) => {
  const actor = actors.administrator;
  await setupApiMock(page, actor);
  await loginUser(page, actor.username);

  await page.setViewportSize({ width: 1440, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await capture(page, 'dashboard-viewport-1440.png');

  await page.setViewportSize({ width: 1024, height: 768 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await capture(page, 'dashboard-viewport-1024.png');

  await page.setViewportSize({ width: 800, height: 600 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await capture(page, 'dashboard-viewport-800.png');
});

test('CA-18: Refresh desde Inicio recupera sesión con /api/auth/me', async ({ page }) => {
  const actor = actors.administrator;
  await setupApiMock(page, actor);
  await loginUser(page, actor.username);

  await page.reload();
  await expect(page.getByRole('heading', { level: 1, name: 'Inicio' })).toBeVisible();
  await expect(page.getByText(`Hola, ${actor.nombre}`)).toBeVisible();
  await capture(page, 'dashboard-refresh-session.png');
});

test('CA-19: Logout elimina la sesión y retorna al login', async ({ page }) => {
  const actor = actors.administrator;
  await setupApiMock(page, actor);
  await loginUser(page, actor.username);

  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(page.getByRole('heading', { name: 'Iniciar sesión' })).toBeVisible();
  const token = await page.evaluate(() => sessionStorage.getItem('optimizador.auth'));
  expect(token).toBeNull();
  await capture(page, 'dashboard-logout.png');
});

test('CA-13, CA-14: Fallo parcial controlado muestra aviso sin comprometer fuentes válidas', async ({ page }) => {
  const actor = actors.administrator;
  await setupApiMock(page, actor, { partialFailPlanchas: true });
  await loginUser(page, actor.username);

  await expect(page.getByText('Información parcial')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Planchas' }).getByRole('alert')).toContainText('No se pudo cargar planchas');
  await expect(page.getByRole('region', { name: 'Retazos' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Pedidos pendientes' })).toBeVisible();
  await capture(page, 'dashboard-partial-error.png');
});
