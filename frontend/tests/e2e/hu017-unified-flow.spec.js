import { test, expect } from '@playwright/test';
import { api, setup, login, open, run, stock, orderStates, capture } from './optimizationRealSupport.js';

test('HU-017 T01: multipedido unificado, inspección honesta y simulación sin consumo', async ({ page }, info) => {
  const data = await setup(page, 'combined');
  const before = await stock(page, data);
  const posts = [];
  page.on('request', request => {
    if (request.method() === 'POST' && new URL(request.url()).pathname.startsWith('/api/optimization/')) posts.push(new URL(request.url()).pathname);
  });
  await login(page, data.actors.all); await open(page);
  await expect(page.getByRole('navigation', { name: 'Herramientas de corte' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Vista previa de piezas', exact: true })).toHaveCount(0);
  await expect(page.getByRole('list', { name: 'Etapas de optimización' })).toBeVisible();
  expect(posts).toEqual([]);
  for (const id of data.orders) await page.getByRole('checkbox', { name: new RegExp(`^#${id} ·`) }).check();
  await page.getByRole('button', { name: 'Revisar vidrios y piezas', exact: true }).click();
  const inspection = page.getByRole('region', { name: 'Inspección de piezas', exact: true });
  await expect(inspection.getByRole('status')).toHaveText('Máscara de la ejecución no disponible para esta pieza.');
  await expect(inspection.getByRole('img', { name: /Geometría original/ })).toHaveCount(1);
  await expect(inspection.getByRole('img', { name: /Detalle de la pieza/ })).toHaveCount(0);
  for (const material of data.materials) {
    await inspection.getByLabel('Vidrio para inspeccionar').selectOption(`${material.id_tipo_vidrio}:${material.espesor_mm}`);
    await expect(inspection.getByRole('img', { name: /Geometría original/ })).toHaveCount(1);
  }
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  expect(posts).toEqual([]);
  expect(await orderStates(page, data)).toEqual(['PENDIENTE', 'PENDIENTE']);
  expect(await stock(page, data)).toEqual(before);

  // The UI requests V2; GET and confirmation remain canonical V1.
  const { result } = await run(page, data, info);
  expect(result.completo).toBe(true);
  expect(result.metodo).toBe('FF');
  expect(posts).toEqual(['/api/optimization/runs']);
  expect(await stock(page, data)).toEqual(before);
  const stages = page.getByRole('list', { name: 'Etapas de optimización' });
  await expect(stages).toContainText('Bases preparadas');
  await expect(stages).toContainText('Evaluaciones recibidas (muestra)');
  const process = page.getByRole('region', { name: 'Proceso visual de optimización', exact: true });
  await expect(process.locator('[data-mask-ref]')).toHaveCount(1);
  await expect(process.locator('[data-run-id]')).toHaveAttribute('data-run-id', String(result.id_optimizacion));
  await expect(stages).toContainText('Resultado completo');
  await expect(page.getByRole('button', { name: 'Confirmar corte', exact: true })).toBeEnabled();
});

test('HU-017: máscara orientada, controles por teclado y recuperación sin recalcular', async ({ page }, info) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const data = await setup(page, 'rotated');
  await login(page, data.actors.all); await open(page);
  let posts = 0;
  page.on('request', request => { if (new URL(request.url()).pathname === '/api/optimization/runs' && request.method() === 'POST') posts++; });
  const { result, events, before } = await run(page, data, info);
  expect(events.every(event => event.schema_version === 2)).toBe(true);
  const region = page.getByRole('region', { name: 'Proceso visual de optimización', exact: true });
  await expect(region.locator('[data-mask-angle]')).toHaveAttribute('data-mask-angle', /^90(?:\.0+)?$/);
  await expect(region.getByRole('img', { name: /Contorno utilizado/ })).toBeVisible();
  expect(await page.locator('[data-placement]').evaluate(element => getComputedStyle(element).animationName)).toBe('none');
  const pause = region.getByRole('button', { name: 'Pausar vista', exact: true });
  await pause.focus(); await page.keyboard.press('Enter');
  await expect(region.getByRole('button', { name: 'Reanudar vista', exact: true })).toBeFocused();
  await page.keyboard.press('Enter');
  const hide = region.getByRole('button', { name: 'Ocultar detalle visual', exact: true });
  await hide.focus(); await page.keyboard.press('Enter');
  await expect(region.getByRole('button', { name: 'Mostrar detalle visual', exact: true })).toBeFocused();
  await expect(region.locator('canvas')).toHaveCount(0);
  await page.keyboard.press('Enter');
  await expect(region.locator('[data-mask-angle]')).toHaveAttribute('data-mask-angle', /^90(?:\.0+)?$/);
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (width === 360 || width === 1440) await capture(page, info, `visual-${width}`, region);
  }
  expect(posts).toBe(1);
  await page.reload(); await open(page);
  await page.getByLabel('Número de trabajo', { exact: true }).fill(String(result.id_optimizacion));
  await page.getByRole('button', { name: 'Consultar resultado', exact: true }).click();
  const recovered = page.getByRole('region', { name: 'Proceso visual de optimización', exact: true });
  await expect(recovered.locator('[data-mask-ref]')).toHaveCount(1);
  await expect(recovered.locator('[data-mask-angle]')).toHaveAttribute('data-mask-angle', /^90(?:\.0+)?$/);
  await expect(page.getByText('Estado del trabajo: Distribución lista', { exact: true })).toBeVisible();
  expect(posts).toBe(1);
  expect(await stock(page, data)).toEqual(before);
});

test('HU-017: el POST sin perfil conserva V1 y sus permisos de consulta', async ({ page }) => {
  const data = await setup(page, 'single');
  const response = await page.request.post(`${api}/api/optimization/runs`, { headers: data.headers, data: { order_ids: data.orders } });
  expect(response.status()).toBe(201);
  const events = (await response.text()).trim().split('\n').map(line => JSON.parse(line));
  expect(events.every(event => event.schema_version === 1)).toBe(true);
  expect(events.some(event => event.event === 'preparation_started')).toBe(false);
  const result = await page.request.get(`${api}${response.headers().location}`, { headers: data.headers });
  expect(result.status()).toBe(200);
  const manifest = await page.request.get(`${api}${response.headers().location}/visual`, { headers: data.headers });
  expect(manifest.status()).toBe(410);
});

test('HU-017 T01: SIN_SOLUCION conserva resultado parcial sin certificar etapas no observadas', async ({ page }, info) => {
  const data = await setup(page, 'incomplete');
  await login(page, data.actors.all); await open(page);
  const { result, before } = await run(page, data, info);
  expect(result.estado).toBe('SIN_SOLUCION');
  const stages = page.getByRole('list', { name: 'Etapas de optimización' });
  await expect(stages).toContainText('Resultado parcial');
  await expect(stages).toContainText('Bases preparadas');
  await expect(page.getByRole('region', { name: 'Piezas sin colocar', exact: true })).toContainText('sin espacio factible');
  await expect(page.getByRole('button', { name: 'Confirmar corte', exact: true })).toHaveCount(0);
  expect(await stock(page, data)).toEqual(before);
  expect(await orderStates(page, data)).toEqual(['PENDIENTE']);
});
