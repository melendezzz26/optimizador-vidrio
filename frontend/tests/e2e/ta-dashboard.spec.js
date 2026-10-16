import { mkdirSync } from 'node:fs';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const appOrigin = 'http://127.0.0.1:5173';
const apiOrigin = 'http://127.0.0.1:8000';
const evidenceDir = fileURLToPath(new URL('../../../docs/evidence/sprint-01/TA-DASHBOARD-001/t3/screenshots/', import.meta.url));
mkdirSync(evidenceDir, { recursive: true });

const roles = {
  administrator: {
    label: 'Administrador',
    username: process.env.TA_DASHBOARD_E2E_ADMIN_USERNAME?.trim(),
    password: process.env.TA_DASHBOARD_E2E_ADMIN_PASSWORD,
    action: 'Gestión de inventario',
    moduleHeading: 'Gesti\u00f3n de Inventario',
    forbidden: [],
  },
  operator: {
    label: 'Operario',
    username: process.env.TA_DASHBOARD_E2E_OPERATOR_USERNAME?.trim(),
    password: process.env.TA_DASHBOARD_E2E_OPERATOR_PASSWORD,
    action: 'Gestión de inventario',
    moduleHeading: 'Gesti\u00f3n de Inventario',
    forbidden: ['Administración'],
  },
  warehouse: {
    label: 'Almacenero',
    username: process.env.TA_DASHBOARD_E2E_WAREHOUSE_USERNAME?.trim(),
    password: process.env.TA_DASHBOARD_E2E_WAREHOUSE_PASSWORD,
    action: 'Gestión de inventario',
    moduleHeading: 'Gestión de Inventario',
    forbidden: ['Registro de pedidos', 'Administración'],
  },
};

const hasCredentials = role => Boolean(role.username && role.password);
const dashboardPaths = new Set([
  '/api/inventory/planchas', '/api/inventory/retazos', '/api/orders', '/api/clients',
]);

function watchDashboardResponses(page) {
  const responses = [];
  page.on('response', response => {
    const url = new URL(response.url());
    if (url.origin === apiOrigin && response.request().method() === 'GET' && dashboardPaths.has(url.pathname)) {
      responses.push({ path: url.pathname, status: response.status() });
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
  await expect(page.locator('aside.ng-sidebar').getByRole('button', { name: 'Inicio', exact: true }))
    .toHaveAttribute('aria-current', 'page');
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
  await expect(page.locator('.dashboard-page [role="status"]')).toHaveCount(0);
}

async function capture(page, filename) {
  await page.screenshot({
    path: `${evidenceDir}/${filename}`,
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
    test.skip(!hasCredentials(role), `E2E real requiere credenciales de prueba configuradas para ${role.label}`);
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
  });
}

test('refresh conserva sesión real mediante GET /api/auth/me', async ({ page }) => {
  const role = roles.administrator;
  test.skip(!hasCredentials(role), 'E2E real requiere credenciales de prueba configuradas para Administrador');
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
  test.skip(!hasCredentials(role), 'E2E real requiere credenciales de prueba configuradas para Administrador');
  await restrictOrigins(page);
  const responses = watchDashboardResponses(page);
  await signIn(page, role);
  await waitForRealDashboard(page, responses, role);
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Iniciar sesión', exact: true })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('optimizador.auth'))).toBeNull();
  await capture(page, 'dashboard-logout.png');
});

test('Dashboard real se adapta a desktop 1366 y mobile 390 sin overflow', async ({ page }) => {
  const role = roles.administrator;
  test.skip(!hasCredentials(role), 'E2E real requiere credenciales de prueba configuradas para Administrador');
  await restrictOrigins(page);
  const responses = watchDashboardResponses(page);
  await signIn(page, role);
  await waitForRealDashboard(page, responses, role);
  await page.setViewportSize({ width: 1366, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await capture(page, 'dashboard-desktop-1366.png');
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Resumen operativo' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Abrir Gestión de inventario', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await capture(page, 'dashboard-mobile-390.png');
});

test('CONTROLLED FAILURE SCENARIO — NOT REAL BACKEND FAILURE: muestra error parcial conservando otras fuentes reales', async ({ page }) => {
  const role = roles.administrator;
  test.info().annotations.push({ type: 'scenario', description: 'CONTROLLED FAILURE SCENARIO — NOT REAL BACKEND FAILURE' });
  test.skip(!hasCredentials(role), 'E2E real requiere credenciales de prueba configuradas para Administrador');
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
  expect(responses.filter(response => response.path === '/api/inventory/planchas')).toEqual([{ path: '/api/inventory/planchas', status: 503 }]);
  expect(responses.filter(response => response.path !== '/api/inventory/planchas').every(response => response.status === 200)).toBe(true);
  await expect(page.getByText('Información parcial', { exact: true })).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('No se pudo cargar planchas');
  await expect(page.getByRole('heading', { name: 'Resumen operativo' })).toBeVisible();
  await capture(page, 'dashboard-partial-error.png');
});
