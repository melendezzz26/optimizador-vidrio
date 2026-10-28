import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const api = 'http://127.0.0.1:8017';
test.beforeEach(async ({ page, baseURL }) => {
  await page.route('**/*', route => [baseURL, api].includes(new URL(route.request().url()).origin) ? route.continue() : route.abort());
  await page.goto('/');
  await page.getByLabel('Usuario', { exact: true }).fill('A70000003');
  await page.getByLabel('Contraseña', { exact: true }).fill('Admin-test-2026!');
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click();
  await page.getByRole('button', { name: 'Registro de pedidos', exact: true }).click();
  await page.getByRole('button', { name: 'Nuevo pedido', exact: true }).click();
  await page.getByLabel('Nombre del cliente').fill('Vidrios Norte');
  await page.getByRole('button', { name: 'Buscar', exact: true }).click();
  await page.getByRole('button', { name: 'Seleccionar Vidrios Norte' }).click();
  await page.getByLabel('Tipo de vidrio', { exact: true }).selectOption('7');
  await page.getByLabel('Espesor del vidrio (mm)', { exact: true }).selectOption('5.5');
});

test('editar tres veces conserva ID, cantidad de pedidos y selección en optimización', async ({ page }) => {
  // Existing helper verifies ownership of the disposable loopback database and
  // supplies the approved configuration required to execute a real cut.
  execFileSync('python', ['-m', 'tests.optimization_e2e_data', 'single'], {
    cwd: fileURLToPath(new URL('../../../backend/', import.meta.url)), encoding: 'utf8',
  });
  await page.getByLabel('Ancho (mm)', { exact: true }).fill('100');
  await page.getByLabel('Alto (mm)', { exact: true }).fill('200');
  const created = page.waitForResponse(response => response.url() === `${api}/api/orders` && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Guardar pedido', exact: true }).click();
  const response = await created;
  expect(response.status()).toBe(201);
  const { id_pedido } = await response.json();
  const headers = { Authorization: response.request().headers().authorization };
  const listing = async () => {
    const result = await page.request.get(`${api}/api/orders?estado=PENDIENTE&limit=100`, { headers });
    expect(result.status()).toBe(200);
    return result.json();
  };
  const before = await listing();
  const writes = [];
  page.on('request', request => { if (/\/api\/orders(?:\/\d+)?$/.test(request.url()) && ['POST', 'PUT'].includes(request.method())) writes.push(request); });
  for (const width of [120, 140, 160]) {
    await page.getByRole('button', { name: `Editar pedido ${id_pedido}`, exact: true }).click();
    const dialog = page.getByRole('dialog', { name: `Pedido #${id_pedido} · Editar`, exact: true });
    await dialog.locator('.orders-group-toggle').click();
    await dialog.getByLabel('Ancho (mm)', { exact: true }).fill(String(width));
    const saved = page.waitForResponse(result => result.url() === `${api}/api/orders/${id_pedido}` && result.request().method() === 'PUT');
    await dialog.getByRole('button', { name: 'Guardar cambios', exact: true }).click();
    const updated = await saved;
    expect(updated.status()).toBe(200);
    expect((await updated.json()).id_pedido).toBe(id_pedido);
    await expect(dialog).toHaveCount(0);
    const read = await page.request.get(`${api}/api/orders/${id_pedido}`, { headers });
    const order = await read.json();
    expect(order.id_pedido).toBe(id_pedido);
    expect(order.piezas[0].dimensiones.width_mm).toBe(width);
    const after = await listing();
    expect(after.total).toBe(before.total);
    expect(after.items.filter(order => order.id_pedido === id_pedido)).toHaveLength(1);
  }
  expect(writes.map(request => request.method())).toEqual(['PUT', 'PUT', 'PUT']);
  await page.getByRole('button', { name: 'Optimización', exact: true }).click();
  const pending = page.getByRole('list', { name: 'Pedidos pendientes', exact: true });
  const orderRow = pending.getByRole('listitem').filter({ hasText: `#${id_pedido} ·` });
  await expect(orderRow).toHaveCount(1);
  await orderRow.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Revisar vidrios y piezas', exact: true }).click();
  const run = page.waitForResponse(result => {
    const url = new URL(result.url());
    return url.origin === api && url.pathname === '/api/optimization/runs' && result.request().method() === 'POST';
  });
  await page.getByRole('button', { name: 'Calcular distribución', exact: true }).click();
  const calculated = await run;
  expect(new URL(calculated.url()).searchParams.get('stream_profile')).toBe('visual-v2');
  expect(calculated.status()).toBe(201);
  expect(calculated.request().postDataJSON()).toEqual({ order_ids: [id_pedido] });
  await page.getByRole('button', { name: 'Ver en 3D', exact: true }).click();
  await expect(page.getByRole('list', { name: 'Piezas en la vista 3D', exact: true })).toContainText('160 × 200 mm');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('crear polígono actualiza medidas parciales y mantiene referencia provisional', async ({ page }) => {
  await page.getByLabel('Forma', { exact: true }).selectOption('POLIGONO_CONVEXO');
  const canvas = page.getByRole('img', { name: 'Lienzo del dibujo original', exact: true });
  await canvas.scrollIntoViewIfNeeded();
  for (const point of [[100, 100], [400, 100], [400, 300], [100, 300]]) {
    const position = await canvas.evaluate((svg, [x, y]) => {
      const point = new DOMPoint(x, y).matrixTransform(svg.getScreenCTM());
      return { x: point.x, y: point.y };
    }, point);
    await page.mouse.click(position.x, position.y);
  }
  await page.getByRole('button', { name: 'Cerrar polígono', exact: true }).focus();
  await page.keyboard.press('Enter');
  const view = page.getByRole('img', { name: 'Vista dimensional de la pieza', exact: true });
  const polygon = view.locator('polygon');
  const sketchReference = view.locator('.custom-piece-editor__sketch-reference');
  const referenceShape = () => sketchReference.evaluate(polyline => {
    const points = Array.from(polyline.points, ({ x, y }) => [x, y]);
    const minX = Math.min(...points.map(([x]) => x));
    const minY = Math.min(...points.map(([, y]) => y));
    const scale = Math.max(
      Math.max(...points.map(([x]) => x)) - minX,
      Math.max(...points.map(([, y]) => y)) - minY,
    );
    if (!Number.isFinite(scale) || scale <= 0) throw new Error('Reference must be a nondegenerate sketch');
    // Remove only translation and uniform responsive scaling. A single scale
    // preserves aspect ratio, angles, vertex order and the closing vertex.
    return points.map(([x, y]) => [(x - minX) / scale, (y - minY) / scale]);
  });
  const reference = await referenceShape();
  const field = i => page.getByLabel(`Longitud del segmento S${i} en milímetros`, { exact: true });
  await expect(field(1)).toBeFocused();
  await field(1).fill('300');
  await expect(view).toContainText('S1 · 300 mm');
  const first = await polygon.getAttribute('points');
  await field(2).fill('150');
  await expect(polygon).not.toHaveAttribute('points', first);
  await expect(polygon).toHaveAttribute('data-provisional', 'true');
  // ResizeObserver can update the SVG viewBox after closing the mobile canvas.
  // Compare the sketch shape, not pixel coordinates from an earlier layout.
  await expect.poll(referenceShape).toEqual(
    reference.map(point => point.map(coordinate => expect.closeTo(coordinate, 8))),
  );
  await expect(field(3)).toHaveValue('');
  await expect(page.getByRole('button', { name: 'Agregar pieza al pedido', exact: true })).toBeDisabled();
  await field(2).fill('170');
  const second = await polygon.getAttribute('points');
  await field(2).fill('150');
  await expect(polygon).not.toHaveAttribute('points', second);
  await field(3).fill('300');
  await field(4).fill('150');
  await expect(polygon).toHaveAttribute('data-provisional', 'false');
  await expect(sketchReference).toHaveCount(0);
  await expect(page.getByText('✓ Geometría validada y lista.')).toBeVisible();
  await page.getByRole('button', { name: 'Agregar pieza al pedido', exact: true }).click();
  await expect(page.getByText('✓ Figura configurada')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
