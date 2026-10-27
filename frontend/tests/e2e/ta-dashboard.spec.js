import { mkdirSync } from 'node:fs';
import process from 'node:process';
import path from 'node:path';
import { expect, test } from '@playwright/test';

const appOrigin = 'http://127.0.0.1:5173';
// These actors exist only in tests.e2e_server's owned loopback PostgreSQL.
// Missing setup must fail the suite instead of silently skipping acceptance tests.
const apiOrigin = 'http://127.0.0.1:8017';
const evidenceDir = process.env.NEWGLASS_HU016_EVIDENCE_DIR;

const roles = {
  administrator: {
    label: 'Administrador',
    username: 'A70000003',
    password: 'Admin-test-2026!',
    action: 'Gestión de inventario',
    moduleHeading: 'Gesti\u00f3n de Inventario',
    forbidden: [],
  },
  operator: {
    label: 'Operario',
    username: 'O70000001',
    password: 'Orders-test-2026!',
    action: 'Gestión de inventario',
    moduleHeading: 'Gesti\u00f3n de Inventario',
    forbidden: ['Administración'],
  },
  warehouse: {
    label: 'Almacenero',
    username: 'A70000002',
    password: 'Inventory-test-2026!',
    action: 'Gestión de inventario',
    moduleHeading: 'Gestión de Inventario',
    forbidden: ['Registro de pedidos', 'Administración'],
  },
};

const noFunctions = { label: 'Sin funciones E2E', username: 'O70000004', password: 'Dashboard-test-2026!' };
const dashboardPaths = new Set([
  '/api/inventory/planchas', '/api/inventory/retazos', '/api/orders', '/api/clients',
]);

function watchDashboardResponses(page) {
  const responses = [];
  page.on('response', response => {
    const url = new URL(response.url());
    if (url.origin === apiOrigin && response.request().method() === 'GET' && dashboardPaths.has(url.pathname)) {
      responses.push({ path: url.pathname, query: url.searchParams, status: response.status(), response });
    }
  });
  return responses;
}

async function restrictOrigins(page) {
  await page.route('**/*', route => {
    const origin = new URL(route.request().url()).origin;
    return [appOrigin, apiOrigin].includes(origin) ? route.fallback() : route.abort();
  });
}

async function signIn(page, role) {
  const loginResponse = page.waitForResponse(response => response.url() === `${apiOrigin}/api/auth/login`
    && response.request().method() === 'POST');
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Iniciar sesión' })).toBeVisible();
  await page.getByLabel('Usuario', { exact: true }).fill(role.username);
  await page.getByLabel('Contraseña', { exact: true }).fill(role.password);
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click();
  const response = await loginResponse;
  expect(response.status()).toBe(200);
  await expect(page.getByRole('heading', { name: 'Inicio', exact: true })).toBeVisible();
  await expect(page.locator('.session-bar')).toContainText(role.label);
  const session = await response.json();
  await expect(page.getByText(`Hola, ${session.usuario.nombre}`, { exact: true })).toBeVisible();
  await expect(page.locator('aside.ng-sidebar').getByRole('button', { name: 'Inicio', exact: true }))
    .toHaveAttribute('aria-current', 'page');
  return session;
}

async function waitForRealDashboard(page, responses, role) {
  const expectedResponseCount = role.label === 'Almacenero' ? 2 : 6;
  await expect.poll(() => responses.length, { timeout: 30_000 }).toBe(expectedResponseCount);
  expect(responses.every(response => response.status === 200)).toBe(true);
  expect(responses.filter(response => response.path === '/api/inventory/planchas')).toHaveLength(1);
  expect(responses.filter(response => response.path === '/api/inventory/retazos')).toHaveLength(1);
  if (role.label === 'Almacenero') {
    expect(responses.some(response => response.path === '/api/orders' || response.path === '/api/clients')).toBe(false);
  } else {
    expect(responses.filter(response => response.path === '/api/orders')).toHaveLength(3);
    expect(responses.filter(response => response.path === '/api/clients')).toHaveLength(1);
  }
  await expect(page.getByRole('heading', { name: 'Resumen operativo' })).toBeVisible();
  // Empty sources legitimately expose role=status; only the loader must finish.
  await expect(page.locator('.dashboard-page .ng-loading-state')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Actualizar datos', exact: true })).toBeEnabled();
  // Compare rendered figures with the actual responses, not hard-coded seed totals.
  const sheets = await responses.find(item => item.path === '/api/inventory/planchas').response.json();
  const sheetCard = page.locator('.dashboard-summary-card').filter({ has: page.getByRole('heading', { name: 'Planchas', exact: true }) });
  const active = sheets.filter(item => item.estado && item.cantidad > 0);
  const figures = [active.reduce((sum, item) => sum + item.cantidad, 0), active.length, sheets.length];
  const number = new Intl.NumberFormat('es-PE');
  if (sheets.length) await expect(sheetCard.locator('dd')).toHaveText(figures.map(value => number.format(value)));
  for (const [state, title, empty] of [
    ['PENDIENTE', 'Pedidos pendientes', 'No hay pedidos pendientes.'],
    ['EN_OPTIMIZACION', 'Pedidos en optimización', 'No hay pedidos en optimización.'],
  ]) {
    if (role.label === 'Almacenero') {
      await expect(page.getByRole('heading', { name: title, exact: true })).toHaveCount(0);
    } else {
      const result = await responses.find(item => item.path === '/api/orders' && item.query.get('estado') === state).response.json();
      const card = page.locator('.dashboard-summary-card').filter({ has: page.getByRole('heading', { name: title, exact: true }) });
      if (result.total) await expect(card.locator('dd')).toHaveText(number.format(result.total));
      else await expect(card.getByText(empty, { exact: true })).toBeVisible();
    }
  }
}

async function capture(page, filename) {
  const info = test.info();
  const directory = evidenceDir ? path.join(evidenceDir, info.project.name) : info.outputPath();
  mkdirSync(directory, { recursive: true });
  await page.screenshot({
    path: path.join(directory, filename),
    fullPage: true,
    animations: 'disabled',
    maskColor: '#cbd5e1',
    mask: [
      page.locator('.session-bar-name'),
      page.locator('.session-bar-details div:first-child dd'),
      page.locator('.dashboard-order-identity p'),
    ],
  });
}

for (const [key, role] of Object.entries(roles)) {
  test(`Dashboard real para ${role.label}: datos, permisos y navegación`, async ({ page }) => {
    await restrictOrigins(page);
    const responses = watchDashboardResponses(page);
    await signIn(page, role);
    await waitForRealDashboard(page, responses, role);

    const shortcuts = page.getByRole('region', { name: 'Accesos rápidos' });
    await expect(shortcuts.getByRole('button', { name: `Abrir ${role.action}`, exact: true })).toBeVisible();
    for (const forbidden of role.forbidden) {
      await expect(shortcuts.getByRole('button', { name: `Abrir ${forbidden}`, exact: true })).toHaveCount(0);
    }
    await capture(page, `dashboard-${key === 'administrator' ? 'administrador' : key === 'operator' ? 'operario' : 'almacenero'}.png`);

    const moduleResponse = page.waitForResponse(response => {
      const url = new URL(response.url());
      return url.origin === apiOrigin && response.request().method() === 'GET'
        && url.pathname === '/api/inventory/planchas';
    });
    await shortcuts.getByRole('button', { name: `Abrir ${role.action}`, exact: true }).click();
    await expect(page.getByRole('heading', { name: role.moduleHeading, exact: true })).toBeVisible();
    await expect(page.locator('aside.ng-sidebar').getByRole('button', { name: role.action, exact: true }))
      .toHaveAttribute('aria-current', 'page');
    expect((await moduleResponse).status()).toBe(200);
    await expect(page.locator('.inventory-list [role="status"]')).toContainText('Mostrando');
    const screenshotName = key === 'administrator' ? 'administrador' : key === 'operator' ? 'operario' : 'almacenero';
    await capture(page, `dashboard-${screenshotName}-${key === 'warehouse' ? 'inventario' : 'navegacion'}.png`);

    responses.length = 0;
    await page.getByRole('button', { name: 'Inicio', exact: true }).click();
    await waitForRealDashboard(page, responses, role);
    await expect(page.getByRole('button', { name: 'Inicio', exact: true })).toHaveAttribute('aria-current', 'page');
    await page.getByRole('button', { name: 'Abrir Optimización', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Optimización de corte', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Optimización', exact: true })).toHaveAttribute('aria-current', 'page');
    if (key === 'warehouse') {
      await expect(page.getByRole('button', { name: 'Revisar vidrios y piezas', exact: true })).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Calcular distribución', exact: true })).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Confirmar corte', exact: true })).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Consultar resultado', exact: true })).toBeVisible();
    }
    await capture(page, `dashboard-${screenshotName}-optimizacion.png`);
    responses.length = 0;
    await page.getByRole('button', { name: 'Inicio', exact: true }).click();
    await waitForRealDashboard(page, responses, role);
    for (const [action, heading, resource] of [
      ...(key !== 'warehouse' ? [['Registro de pedidos', 'Gestión de pedidos', '/api/orders']] : []),
      ...(key === 'administrator' ? [['Administración', 'Gestión de usuarios', '/api/users']] : []),
    ]) {
      const loaded = page.waitForResponse(response => new URL(response.url()).pathname === resource && response.request().method() === 'GET');
      await page.getByRole('button', { name: `Abrir ${action}`, exact: true }).click();
      await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
      expect((await loaded).status()).toBe(200);
      responses.length = 0;
      await page.getByRole('button', { name: 'Inicio', exact: true }).click();
      await waitForRealDashboard(page, responses, role);
    }
  });
}

test('refresh conserva sesión real mediante GET /api/auth/me', async ({ page }) => {
  const role = roles.administrator;
  await restrictOrigins(page);
  const responses = watchDashboardResponses(page);
  await signIn(page, role);
  await waitForRealDashboard(page, responses, role);
  const meResponse = page.waitForResponse(response => response.url() === `${apiOrigin}/api/auth/me`
    && response.request().method() === 'GET');
  responses.splice(0, responses.length);
  await page.reload();
  expect((await meResponse).status()).toBe(200);
  await waitForRealDashboard(page, responses, role);
  await expect(page.getByRole('heading', { name: 'Inicio', exact: true })).toBeVisible();
  await expect(page.locator('.session-bar')).toContainText('Administrador');
  await capture(page, 'dashboard-refresh-session.png');
});

test('logout elimina la sesión real y devuelve al login', async ({ page }) => {
  const role = roles.administrator;
  await restrictOrigins(page);
  const responses = watchDashboardResponses(page);
  await signIn(page, role);
  await waitForRealDashboard(page, responses, role);
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Iniciar sesión', exact: true })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('optimizador.auth'))).toBeNull();
  await capture(page, 'dashboard-logout.png');
});

for (const width of [1440, 1024, 800, 390]) {
  test(`Dashboard real a ${width}px: sin overflow y Sidebar utilizable`, async ({ page }) => {
    const role = roles.administrator;
    await page.setViewportSize({ width, height: 900 });
    await restrictOrigins(page);
    const responses = watchDashboardResponses(page);
    await signIn(page, role);
    await waitForRealDashboard(page, responses, role);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const sidebar = page.getByRole('complementary', { name: 'Módulos de NewGlass' });
    await expect(sidebar.getByRole('button', { name: 'Inicio', exact: true })).toBeInViewport();
    const shortcut = page.getByRole('button', { name: 'Abrir Gestión de inventario', exact: true });
    await shortcut.scrollIntoViewIfNeeded();
    await expect(shortcut).toBeInViewport();
    const sideBox = await sidebar.boundingBox();
    const mainBox = await page.locator('.dashboard-page').boundingBox();
    const overlapX = Math.min(sideBox.x + sideBox.width, mainBox.x + mainBox.width) - Math.max(sideBox.x, mainBox.x);
    const overlapY = Math.min(sideBox.y + sideBox.height, mainBox.y + mainBox.height) - Math.max(sideBox.y, mainBox.y);
    expect(overlapX <= 1 || overlapY <= 1).toBe(true);
    await capture(page, `dashboard-viewport-${width}.png`);
    await sidebar.getByRole('button', { name: 'Gestión de inventario', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Gestión de Inventario', exact: true })).toBeVisible();
    await expect(page.locator('.inventory-list [role="status"]')).toContainText('Mostrando');
    responses.length = 0;
    await page.getByRole('button', { name: 'Inicio', exact: true }).click();
    await waitForRealDashboard(page, responses, role);
  });
}

test('sesión real sin permisos conserva Inicio y logout sin consultar módulos restringidos', async ({ page }) => {
  await restrictOrigins(page);
  const restricted = [];
  page.on('request', request => {
    const url = new URL(request.url());
    if (url.origin === apiOrigin && url.pathname.startsWith('/api/') && !url.pathname.startsWith('/api/auth/')) {
      restricted.push(url.pathname);
    }
  });
  const session = await signIn(page, noFunctions);
  expect(session.usuario.permisos).toEqual([]);
  await expect(page.getByText('Sin funciones habilitadas', { exact: true })).toBeVisible();
  await expect(page.locator('aside.ng-sidebar button')).toHaveCount(1);
  await expect(page.getByRole('region', { name: 'Accesos rápidos' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Actualizar datos', exact: true })).toHaveCount(0);
  await capture(page, 'dashboard-sin-funciones.png');
  const me = page.waitForResponse(`${apiOrigin}/api/auth/me`);
  await page.reload();
  expect((await me).status()).toBe(200);
  await expect(page.getByText('Sin funciones habilitadas', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Iniciar sesión', exact: true })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('optimizador.auth'))).toBeNull();
  expect(restricted).toEqual([]);
  // Real API authorization remains authoritative even if a client calls it directly.
  const headers = { Authorization: `Bearer ${session.access_token}` };
  for (const resource of ['/api/inventory/planchas', '/api/inventory/retazos', '/api/orders', '/api/clients', '/api/users']) {
    const response = await page.request.get(`${apiOrigin}${resource}`, { headers });
    expect(response.status(), resource).toBe(403);
  }
});

test('CONTROLLED FAILURE SCENARIO — NOT REAL BACKEND FAILURE: muestra error parcial conservando otras fuentes reales', async ({ page }) => {
  const role = roles.administrator;
  test.info().annotations.push({ type: 'scenario', description: 'CONTROLLED FAILURE SCENARIO — NOT REAL BACKEND FAILURE' });
  await restrictOrigins(page);
  await page.route(`${apiOrigin}/api/inventory/planchas`, route => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Simulación controlada de error parcial' }),
    });
  });
  const responses = watchDashboardResponses(page);
  await signIn(page, role);
  await expect.poll(() => responses.length, { timeout: 30_000 }).toBe(6);
  expect(responses.filter(response => response.path === '/api/inventory/planchas').map(({ path, status }) => ({ path, status })))
    .toEqual([{ path: '/api/inventory/planchas', status: 503 }]);
  expect(responses.filter(response => response.path !== '/api/inventory/planchas').every(response => response.status === 200)).toBe(true);
  await expect(page.getByText('Información parcial', { exact: true })).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('No se pudo cargar planchas');
  await expect(page.getByRole('heading', { name: 'Resumen operativo' })).toBeVisible();
  await capture(page, 'dashboard-partial-error.png');
  await page.unroute(`${apiOrigin}/api/inventory/planchas`);
  responses.length = 0;
  await page.getByRole('button', { name: 'Reintentar carga', exact: true }).click();
  await waitForRealDashboard(page, responses, role);
  await expect(page.getByText('Información parcial', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('alert')).toHaveCount(0);
});
