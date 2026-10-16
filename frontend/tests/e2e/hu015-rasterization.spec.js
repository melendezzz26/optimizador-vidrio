import process from 'node:process';
import { expect, test } from '@playwright/test';
import { capture } from './optimizationRealSupport.js';

const apiOrigin = 'http://127.0.0.1:8017';
const username = process.env.HU015_E2E_USERNAME?.trim();
const password = process.env.HU015_E2E_PASSWORD;
const hasHu015Credentials = Boolean(username && password);
const credentials = { username, password };
const glass = { id_tipo_vidrio: 7, espesor_mm: 6 };

async function createPersistedOrder(page, piezas) {
  const login = await page.request.post(`${apiOrigin}/api/auth/login`, { data: credentials });
  expect(login.status()).toBe(200);
  const { access_token: token } = await login.json();
  const headers = { Authorization: `Bearer ${token}` };
  const created = await page.request.post(`${apiOrigin}/api/orders`, {
    headers,
    data: { id_cliente: 41, piezas },
  });
  expect(created.status()).toBe(201);
  const { id_pedido: orderId } = await created.json();
  const details = await page.request.get(`${apiOrigin}/api/orders/${orderId}`, { headers });
  expect(details.status()).toBe(200);
  return details.json();
}

async function signInAndOpenOptimization(page, baseURL) {
  await page.route('**/*', route => {
    const origin = new URL(route.request().url()).origin;
    return [baseURL, apiOrigin].includes(origin) ? route.continue() : route.abort();
  });
  await page.goto('/');
  await page.getByLabel('Usuario', { exact: true }).fill(credentials.username);
  await page.getByLabel('Contraseña', { exact: true }).fill(credentials.password);
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click();
  await page.getByRole('button', { name: 'Optimización', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Optimización' })).toBeVisible();
  await page.getByRole('button', { name: 'Rasterización de piezas', exact: true }).click();
}

function waitForRasterResponse(page) {
  return page.waitForResponse(response => response.url() === `${apiOrigin}/api/optimization/rasterize`
    && response.request().method() === 'POST');
}

async function tabTo(page, locator) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (await locator.evaluate(element => element === document.activeElement)) return;
    await page.keyboard.press('Tab');
  }
  await expect(locator).toBeFocused();
}

test('HU-015: flujo real de pieza cantidad 5, raster, recuperación, resolución y responsive', async ({ page, baseURL }, info) => {
  test.skip(!hasHu015Credentials, 'HU-015 real E2E requires configured synthetic test credentials');
  const order = await createPersistedOrder(page, [
    { tipo_forma: 'RECTANGULO', cantidad: 5, ...glass, width_mm: 800, height_mm: 600 },
    { tipo_forma: 'RECTANGULO', cantidad: 1, ...glass, width_mm: 1, height_mm: 10 },
  ]);
  const [largePiece, thinPiece] = order.piezas;
  const startStatuses = [];
  page.on('response', response => {
    if (response.url() === `${apiOrigin}/api/optimization/start` && response.request().method() === 'POST') {
      startStatuses.push(response.status());
    }
  });
  await signInAndOpenOptimization(page, baseURL);
  const pendingOrder = page.getByRole('button', { name: new RegExp(`Pedido #${order.id_pedido}`) });
  await expect(pendingOrder).toBeVisible();
  const piecesTable = page.getByRole('table', { name: `Piezas del pedido #${order.id_pedido}` });
  // The order has two persisted piece rows. Quantity five stays an attribute of one row.
  const startButton = page.getByRole('button', { name: 'Iniciar optimización' });
  await expect(startButton).toBeDisabled();

  // Use keyboard navigation for selection, start, piece choice, resolution and raster action.
  const refresh = page.getByRole('button', { name: 'Actualizar pedidos' });
  await refresh.focus();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Recuperar proceso iniciado' })).toBeFocused();
  await tabTo(page, pendingOrder);
  await expect(pendingOrder).toBeFocused();
  expect(await pendingOrder.evaluate(element => element.matches(':focus-visible'))).toBe(true);
  await page.keyboard.press('Enter');
  await expect(piecesTable).toBeVisible();
  await expect(piecesTable.getByRole('row', { name: new RegExp(`#${largePiece.id_pieza}.*5`) })).toHaveCount(1);
  await expect(piecesTable.getByRole('row')).toHaveCount(3);
  await tabTo(page, startButton);
  await expect(startButton).toBeFocused();
  const startResponse = page.waitForResponse(response => response.url() === `${apiOrigin}/api/optimization/start`
    && response.request().method() === 'POST');
  await page.keyboard.press('Enter');
  expect((await startResponse).status()).toBe(200);
  await expect(page.getByText('EN OPTIMIZACIÓN', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Pieza persistida')).toBeEnabled();
  expect(startStatuses).toEqual([200]);

  const pieceSelect = page.getByLabel('Pieza persistida');
  await tabTo(page, pieceSelect);
  await expect(pieceSelect).toBeFocused();
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Enter');
  await expect(pieceSelect).toHaveValue(String(largePiece.id_pieza));
  const resolution = page.getByLabel('Resolución raster (mm/celda)');
  await tabTo(page, resolution);
  await expect(resolution).toBeFocused();
  await expect(resolution).toHaveValue('5');
  const rasterButton = page.getByRole('button', { name: 'Rasterizar pieza' });
  await tabTo(page, rasterButton);
  await expect(rasterButton).toBeFocused();
  const emptyMask = page.getByText('Rasteriza la pieza seleccionada para visualizar su máscara.');
  await expect(page.getByRole('img', { name: `Geometría original de la pieza #${largePiece.id_pieza}` })).toBeVisible();
  await expect(emptyMask).toBeVisible();

  await resolution.fill('0.001');
  await tabTo(page, rasterButton);
  const rejectedRequest = waitForRasterResponse(page);
  await page.keyboard.press('Enter');
  const rejected = await rejectedRequest;
  expect(rejected.status()).toBe(422);
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByRole('img', { name: `Geometría original de la pieza #${largePiece.id_pieza}` })).toBeVisible();
  await expect(page.getByText('Rasteriza la pieza seleccionada para visualizar su máscara.')).toBeVisible();
  await expect(page.getByRole('img', { name: /Máscara raster/ })).toHaveCount(0);

  await resolution.fill('5');
  await tabTo(page, rasterButton);
  const successRequest = waitForRasterResponse(page);
  await page.keyboard.press('Enter');
  const success = await successRequest;
  expect(success.status()).toBe(200);
  const result = await success.json();
  expect(result).toMatchObject({ id_pedido: order.id_pedido, id_pieza: largePiece.id_pieza, cantidad: 5, row_count: 120, columns: 160, occupied_cells: 19200 });
  const resultRegion = page.getByRole('region', { name: 'Resultado técnico raster' });
  await expect(resultRegion).toContainText('Cantidad');
  await expect(resultRegion).toContainText('19200');
  await expect(resultRegion).toContainText('5 mm/celda');
  await expect(resultRegion).toContainText('Material de prueba');
  await expect(resultRegion).toContainText('6.0 mm');
  const geometryImage = page.getByRole('img', { name: `Geometría original de la pieza #${largePiece.id_pieza}` });
  const maskImage = page.getByRole('img', { name: `Máscara raster de la pieza #${largePiece.id_pieza}` });
  await expect(geometryImage.locator('rect')).toHaveAttribute('width', '800');
  await expect(geometryImage.locator('rect')).toHaveAttribute('height', '600');
  await expect(maskImage).toBeVisible();
  await capture(page, info, 'raster-rectangle', resultRegion);
  await expect(page.getByText(/cantidad 5\./i)).toHaveCount(1);
  await expect(geometryImage).toHaveCount(1);
  await expect(maskImage).toHaveCount(1);

  for (const width of [1440, 1024, 800]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(maskImage).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    const columns = await page.locator('.optimization-preview-grid').evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length);
    expect(columns).toBe(width <= 900 ? 1 : 2);
  }

  await resolution.fill('10');
  await expect(page.getByRole('img', { name: /Máscara raster/ })).toHaveCount(0);
  await expect(page.getByText('Rasteriza la pieza seleccionada para visualizar su máscara.')).toBeVisible();
  const rerasterRequest = waitForRasterResponse(page);
  await rasterButton.click();
  const reraster = await rerasterRequest;
  expect(reraster.status()).toBe(200);
  expect(await reraster.json()).toMatchObject({ row_count: 60, columns: 80, occupied_cells: 4800 });
  await expect(page.getByRole('img', { name: `Geometría original de la pieza #${largePiece.id_pieza}` })).toBeVisible();
  await expect(page.getByRole('img', { name: `Máscara raster de la pieza #${largePiece.id_pieza}` })).toBeVisible();

  // Browser check near the approved server budget: a 750,000-cell mask is still viewport-sized.
  await resolution.fill('0.8');
  const boundedRequest = waitForRasterResponse(page);
  await rasterButton.click();
  const boundedResponse = await boundedRequest;
  expect(boundedResponse.status()).toBe(200);
  const boundedRaster = await boundedResponse.json();
  expect(boundedRaster.row_count * boundedRaster.columns).toBe(750000);
  const boundedCanvas = page.getByRole('img', { name: `Máscara raster de la pieza #${largePiece.id_pieza}` });
  await expect(boundedCanvas).toBeVisible();
  const canvasSize = await boundedCanvas.evaluate(canvas => ({ width: canvas.width, height: canvas.height }));
  expect(canvasSize.width).toBeLessThan(3000);
  expect(canvasSize.height).toBeLessThan(1000);

  await pieceSelect.selectOption(String(thinPiece.id_pieza));
  await resolution.fill('5');
  await expect(page.getByRole('img', { name: `Geometría original de la pieza #${thinPiece.id_pieza}` }).locator('rect')).toHaveAttribute('width', '1');
  const thinRequest = waitForRasterResponse(page);
  await rasterButton.click();
  const thinResponse = await thinRequest;
  expect(thinResponse.status()).toBe(200);
  expect(await thinResponse.json()).toMatchObject({ row_count: 2, columns: 1, occupied_cells: 2, cantidad: 1 });
  await expect(page.getByRole('img', { name: `Máscara raster de la pieza #${thinPiece.id_pieza}` })).toBeVisible();

  // Leaving and returning discovers the persisted in-progress order without another POST /start.
  const startsBeforeRecovery = startStatuses.length;
  await page.getByRole('button', { name: 'Registro de pedidos', exact: true }).click();
  await page.getByRole('button', { name: 'Optimización', exact: true }).click();
  await page.getByRole('button', { name: 'Rasterización de piezas', exact: true }).click();
  await page.getByRole('button', { name: 'Recuperar proceso iniciado' }).click();
  const recovered = page.getByRole('button', { name: new RegExp(`Pedido #${order.id_pedido}`) });
  await expect(recovered).toBeVisible();
  await recovered.click();
  await expect(page.getByText('EN OPTIMIZACIÓN', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Pieza persistida')).toBeEnabled();
  expect(startStatuses).toHaveLength(startsBeforeRecovery);
});

test('HU-015: CIRCUNFERENCIA se compara con la máscara real del backend', async ({ page, baseURL }, info) => {
  test.skip(!hasHu015Credentials, 'HU-015 real E2E requires configured synthetic test credentials');
  const order = await createPersistedOrder(page, [
    { tipo_forma: 'CIRCUNFERENCIA', cantidad: 2, ...glass, radius_mm: 30 },
  ]);
  const piece = order.piezas[0];
  await signInAndOpenOptimization(page, baseURL);
  await page.getByRole('button', { name: new RegExp(`Pedido #${order.id_pedido}`) }).click();
  await expect(page.getByRole('table', { name: `Piezas del pedido #${order.id_pedido}` })).toBeVisible();
  const startResponse = page.waitForResponse(response => response.url() === `${apiOrigin}/api/optimization/start` && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Iniciar optimización' }).click();
  expect((await startResponse).status()).toBe(200);
  await expect(page.getByLabel('Pieza persistida')).toBeEnabled();
  await page.getByLabel('Pieza persistida').selectOption(String(piece.id_pieza));
  const rasterResponse = waitForRasterResponse(page);
  await page.getByRole('button', { name: 'Rasterizar pieza' }).click();
  expect((await rasterResponse).status()).toBe(200);
  const svg = page.getByRole('img', { name: `Geometría original de la pieza #${piece.id_pieza}` });
  await expect(svg.locator('circle')).toHaveAttribute('r', '30');
  await expect(svg.locator('circle')).toHaveAttribute('cx', '0');
  await expect(svg.locator('circle')).toHaveAttribute('cy', '0');
  await expect(page.getByRole('img', { name: `Máscara raster de la pieza #${piece.id_pieza}` })).toBeVisible();
  await capture(page, info, 'raster-circle', page.getByRole('region', { name: 'Resultado técnico raster' }));
  await expect(page.getByText(/cantidad 2\./i)).toHaveCount(1);
  await expect(svg).toHaveCount(1);
  await expect(page.getByRole('img', { name: `Máscara raster de la pieza #${piece.id_pieza}` })).toHaveCount(1);
});

test('HU-015: POLIGONO_CONVEXO conserva vertices_mm negativos y columnas sobre 53', async ({ page, baseURL }, info) => {
  test.skip(!hasHu015Credentials, 'HU-015 real E2E requires configured synthetic test credentials');
  const vertices = [[-150, -50], [150, -50], [150, 50], [-150, 50]];
  const order = await createPersistedOrder(page, [
    { tipo_forma: 'POLIGONO_CONVEXO', cantidad: 1, ...glass, vertices_mm: vertices },
  ]);
  const piece = order.piezas[0];
  await signInAndOpenOptimization(page, baseURL);
  await page.getByRole('button', { name: new RegExp(`Pedido #${order.id_pedido}`) }).click();
  await expect(page.getByRole('table', { name: `Piezas del pedido #${order.id_pedido}` })).toBeVisible();
  const startResponse = page.waitForResponse(response => response.url() === `${apiOrigin}/api/optimization/start` && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Iniciar optimización' }).click();
  expect((await startResponse).status()).toBe(200);
  await expect(page.getByLabel('Pieza persistida')).toBeEnabled();
  await page.getByLabel('Pieza persistida').selectOption(String(piece.id_pieza));
  const rasterResponse = waitForRasterResponse(page);
  await page.getByRole('button', { name: 'Rasterizar pieza' }).click();
  const response = await rasterResponse;
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.columns).toBeGreaterThan(53);
  expect(result.geometria.vertices_mm).toEqual(vertices);
  await capture(page, info, 'raster-polygon', page.getByRole('region', { name: 'Resultado técnico raster' }));
  const svg = page.getByRole('img', { name: `Geometría original de la pieza #${piece.id_pieza}` });
  await expect(svg.locator('polygon')).toHaveAttribute('points', '-150,-50 150,-50 150,50 -150,50');
  await expect(page.getByRole('img', { name: `Máscara raster de la pieza #${piece.id_pieza}` })).toBeVisible();
});
