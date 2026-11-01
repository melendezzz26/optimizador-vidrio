// Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
import { test, expect } from '@playwright/test';
import { api, setup, login, loginApi, open, stock, capture, save } from './optimizationRealSupport.js';

test('comparar tres motores, revisar fases y solicitud, elegir BF y confirmar una sola vez', async ({ page }, info) => {
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  const data = await setup(page, 'combined', { createOrders: false });
  for (let i = 0; i < 2; i++) {
    const created = await page.request.post(`${api}/api/orders`, { headers: data.headers, data: { id_cliente: 41, piezas: [
      { ...data.materials[0], tipo_forma: 'RECTANGULO', cantidad: 2, width_mm: 50, height_mm: 20 },
      { ...data.materials[1], tipo_forma: 'CIRCUNFERENCIA', cantidad: 1, radius_mm: 10 },
      { ...data.materials[1], tipo_forma: 'POLIGONO_CONVEXO', cantidad: 1, vertices_mm: [[0, 0], [20, 0], [0, 20]] },
    ] } });
    expect(created.status()).toBe(201);
    data.orders.push((await created.json()).id_pedido);
  }
  const before = await stock(page, data);
  await login(page, data.actors.all, { comparative: true }); await open(page);
  for (const id of data.orders) await page.getByRole('checkbox', { name: new RegExp(`Pedido #${id}\\b`) }).check();
  const accepted = page.waitForResponse(r => new URL(r.url()).pathname === '/api/optimization/comparisons' && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar con los tres motores', exact: true }).click();
  const response = await accepted;
  expect(response.status()).toBe(201);
  const current = await response.json(), path = `${api}/api/optimization/comparisons/${current.comparison_id}`;
  await expect(page.getByRole('tab')).toHaveCount(4);
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  const stream = await page.request.get(path + '/events', { headers: data.headers });
  expect(stream.status()).toBe(200);
  const events = (await stream.text()).trim().split('\n').map(line => JSON.parse(line));
  expect(events.filter(e => e.event === 'engine_ready')).toHaveLength(3);
  expect(events.findIndex(e => e.event === 'engine_started')).toBeGreaterThan(events.map(e => e.event).lastIndexOf('engine_ready'));
  for (const method of ['FF', 'BF', 'WF']) {
    const own = events.filter(e => e.method === method), names = own.map(e => e.event);
    expect(names.indexOf('piece_ready')).toBeLessThan(names.indexOf('ordering_ready'));
    expect(names.indexOf('ordering_ready')).toBeLessThan(names.indexOf('piece_placed'));
    expect(new Set(own.map(e => e.execution_id)).size).toBe(1);
  }
  const first = page.getByRole('tabpanel', { name: /First Fit/ });
  await first.getByRole('button', { name: /Máscaras/ }).click();
  await expect(first.locator('[data-mask-ref]')).toHaveCount(1);
  await capture(page, info, 'mascaras-first-fit', first);
  await first.getByRole('button', { name: /Orden de piezas/ }).click();
  await expect(first.getByRole('heading', { name: 'Orden de procesamiento' })).toBeVisible();
  await capture(page, info, 'orden-first-fit', first);
  await first.getByRole('button', { name: /Giros y colocación/ }).click();
  await expect(first.locator('[data-mask-ref]')).toHaveCount(1);
  await first.getByRole('button', { name: 'Pausar vista' }).click();
  await page.getByRole('tab', { name: /Worst Fit/ }).click();
  await page.getByRole('tab', { name: /First Fit/ }).click();
  await expect(first.getByRole('button', { name: 'Reanudar vista' })).toBeVisible();
  await page.getByText(/Piezas y medidas solicitadas/).click();
  await expect(page.getByText('Medidas guardadas del pedido').first()).toBeVisible();
  await expect(page.locator('.comparison-request-grid article')).toHaveCount(6);
  await capture(page, info, 'solicitud-original', page.locator('.comparison-request'));
  await page.getByText(/Piezas y medidas solicitadas/).click();
  await page.getByRole('tab', { name: 'Comparación', exact: true }).click();
  await expect(page.getByRole('radio', { checked: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeDisabled();
  expect(await stock(page, data)).toEqual(before);
  await page.getByLabel('Elegir Best Fit', { exact: true }).click();
  await expect(page.getByLabel('Elegir Best Fit', { exact: true })).toBeChecked();
  await expect(page.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeEnabled();
  expect(await stock(page, data)).toEqual(before);
  await capture(page, info, 'comparacion-antes-de-confirmar');
  const selected = await (await page.request.get(path, { headers: data.headers })).json();
  const best = selected.executions.find(e => e.method === 'BF');
  expect(selected.selected_execution_id).toBe(best.execution_id);
  const nextOrder = await page.request.post(`${api}/api/orders`, { headers: data.headers, data: { id_cliente: 41,
    piezas: [{ ...data.materials[0], tipo_forma: 'RECTANGULO', cantidad: 1, width_mm: 10, height_mm: 10 }] } });
  expect(nextOrder.status()).toBe(201);
  const nextId = (await nextOrder.json()).id_pedido;
  await page.getByRole('button', { name: 'Confirmar distribución elegida' }).click();
  await page.getByRole('alertdialog').getByRole('button', { name: 'Confirmar corte', exact: true }).click();
  await expect(page.getByText(new RegExp(`Trabajo #${current.comparison_id} confirmado`))).toBeVisible();
  await expect(page.getByText(new RegExp(`Trabajo #${current.comparison_id} confirmado`))).toBeInViewport();
  await expect(page.getByRole('tab')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Pedidos pendientes', exact: true })).toBeFocused();
  for (const id of data.orders) await expect(page.getByRole('checkbox', { name: new RegExp(`Pedido #${id}\\b`) })).toHaveCount(0);
  await expect(page.getByRole('checkbox', { name: new RegExp(`Pedido #${nextId}\\b`) })).toBeVisible();
  await capture(page, info, 'confirmacion-limpia-pedidos-pendientes');
  await page.reload(); await open(page);
  await expect(page.getByRole('tab')).toHaveCount(0);
  await page.getByLabel('Consultar trabajo guardado').fill(String(current.comparison_id));
  await page.getByRole('button', { name: 'Consultar', exact: true }).click();
  await expect(page.getByText('Corte confirmado', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Comparación', exact: true }).click();
  await expect(page.getByLabel('Elegir Best Fit', { exact: true })).toBeChecked();
  const done = await (await page.request.get(path, { headers: data.headers })).json();
  expect(done.confirmation.method).toBe('BF');
  expect(done.confirmed).toBe(true);
  expect(done.requested_pieces).toEqual(current.requested_pieces);
  await page.getByText(/Piezas y medidas solicitadas/).click();
  await expect(page.locator('.comparison-request-grid article')).toHaveCount(6);
  await expect(page.getByText('Medidas guardadas del pedido').first()).toBeVisible();
  save(info, 'comparison-events.json', events);
  expect(errors).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await page.getByRole('button', { name: 'Preparar otro trabajo', exact: true }).click();
  await page.getByRole('checkbox', { name: new RegExp(`Pedido #${nextId}\\b`) }).check();
  const newRequest = page.waitForResponse(r => new URL(r.url()).pathname === '/api/optimization/comparisons' && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar con los tres motores', exact: true }).click();
  const newResponse = await newRequest;
  expect(newResponse.status()).toBe(201);
  const newComparison = await newResponse.json();
  expect(newComparison.comparison_id).not.toBe(current.comparison_id);
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Liberar pedidos sin confirmar', exact: true }).click();
  await expect(page.getByText(new RegExp(`Trabajo #${newComparison.comparison_id} liberado sin confirmar`))).toBeVisible();
  await expect(page.getByRole('tab')).toHaveCount(0);
  await expect(page.getByRole('checkbox', { name: new RegExp(`Pedido #${nextId}\\b`) })).not.toBeChecked();
});

test('FF falla al persistir y BF se confirma una vez, regresando al listado', async ({ page }, info) => {
  const data = await setup(page, 'ff-save-failure');
  const before = await stock(page, data);
  await login(page, data.actors.all, { comparative: true }); await open(page);
  await page.getByRole('checkbox', { name: new RegExp(`Pedido #${data.orders[0]}\\b`) }).check();
  const started = page.waitForResponse(r => new URL(r.url()).pathname === '/api/optimization/comparisons' && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar con los tres motores' }).click();
  const current = await (await started).json(), path = `${api}/api/optimization/comparisons/${current.comparison_id}`;
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  await expect(page.getByText(/No se pudo guardar el resultado de este motor/)).toBeVisible();
  expect(await stock(page, data)).toEqual(before);
  await page.getByRole('tab', { name: 'Comparación', exact: true }).click();
  await expect(page.getByLabel('Elegir First Fit', { exact: true })).toBeDisabled();
  await page.getByLabel('Elegir Best Fit', { exact: true }).click();
  await expect(page.getByLabel('Elegir Best Fit', { exact: true })).toBeChecked();
  await expect(page.getByRole('button', { name: 'Confirmar distribución elegida' })).toBeEnabled();
  await capture(page, info, 'ff-fallido-bf-elegido');
  let confirmations = 0;
  page.on('request', request => { if (request.url() === path + '/confirm' && request.method() === 'POST') confirmations++; });
  const confirmed = page.waitForResponse(response => response.url() === path + '/confirm' && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Confirmar distribución elegida' }).click();
  await page.getByRole('alertdialog').getByRole('button', { name: 'Confirmar corte', exact: true }).dblclick();
  const response = await confirmed;
  expect(response.status()).toBe(200);
  await expect(page.getByText(new RegExp(`Trabajo #${current.comparison_id} confirmado`))).toBeVisible();
  await expect(page.getByText(new RegExp(`Trabajo #${current.comparison_id} confirmado`))).toBeInViewport();
  await expect(page.getByRole('tab')).toHaveCount(0);
  expect(confirmations).toBe(1);
  const after = await stock(page, data);
  expect(after.sheets[0].cantidad).toBe(before.sheets[0].cantidad - 1);
  const replay = await page.request.post(path + '/confirm', { headers: { ...data.headers,
    'Idempotency-Key': response.request().headers()['idempotency-key'] }, data: response.request().postDataJSON() });
  expect(replay.status()).toBe(200);
  expect(await replay.json()).toEqual(await response.json());
  expect(await stock(page, data)).toEqual(after);
  const recovered = await (await page.request.get(path, { headers: data.headers })).json();
  expect(recovered.confirmation.method).toBe('BF');
  expect(recovered.executions.find(e => e.method === 'FF').failure_code).toBe('RESULT_SAVE_FAILED');
  await capture(page, info, 'confirmacion-parcial-limpia');
});

test('rotación real de 90 grados y movimiento reducido sin ejecutar otro trabajo al cambiar pestañas', async ({ page }, info) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const data = await setup(page, 'rotated');
  await login(page, data.actors.all, { comparative: true }); await open(page);
  await page.getByRole('checkbox', { name: new RegExp(`Pedido #${data.orders[0]}\\b`) }).check();
  let posts = 0;
  page.on('request', r => { if (new URL(r.url()).pathname === '/api/optimization/comparisons' && r.method() === 'POST') posts++; });
  await page.getByRole('button', { name: 'Comparar con los tres motores' }).click();
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  for (const name of ['First Fit', 'Best Fit', 'Worst Fit']) {
    await page.getByRole('tab', { name: new RegExp(name) }).click();
    const panel = page.getByRole('tabpanel', { name: new RegExp(name) });
    await panel.getByRole('button', { name: /Giros y colocación/ }).click();
    await expect(panel.getByRole('img', { name: /90 grados/ })).toBeVisible();
    await expect(panel.locator('[data-mask-angle]')).toHaveAttribute('data-mask-angle', /^90(?:\.0+)?$/);
    expect(await panel.locator('.comparison-turning-shape').evaluate(e => getComputedStyle(e).transitionDuration)).toBe('0s');
    await capture(page, info, `giro-real-${name.toLowerCase().replaceAll(' ', '-')}`, panel);
  }
  const firstTab = page.getByRole('tab', { name: /First Fit/ });
  await firstTab.focus(); await page.keyboard.press('End');
  await expect(page.getByRole('tab', { name: 'Comparación', exact: true })).toBeFocused();
  await page.keyboard.press('Home');
  await expect(firstTab).toBeFocused();
  expect(posts).toBe(1);
});

test('consulta sin permisos de ejecución recupera resultados sin permitir elección ni consumo', async ({ page }) => {
  const data = await setup(page, 'single');
  const created = await page.request.post(`${api}/api/optimization/comparisons`, { headers: { ...data.headers, 'Idempotency-Key': `view-only-${Date.now()}` }, data: { order_ids: data.orders } });
  expect(created.status()).toBe(201);
  const comparison = await created.json();
  await login(page, data.actors.view, { comparative: true }); await open(page);
  await page.getByLabel('Consultar trabajo guardado').fill(String(comparison.comparison_id));
  await page.getByRole('button', { name: 'Consultar', exact: true }).click();
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Comparación', exact: true }).click();
  await expect(page.getByRole('radio')).toHaveCount(3);
  for (const radio of await page.getByRole('radio').all()) await expect(radio).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Comparar con los tres motores' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Confirmar distribución elegida' })).toHaveCount(0);
  const headers = await loginApi(page.request, data.actors.view);
  const rejected = await page.request.put(`${api}/api/optimization/comparisons/${comparison.comparison_id}/selection`, {
    headers, data: { execution_id: comparison.executions[0].execution_id, expected_version: comparison.version } });
  expect(rejected.status()).toBe(403);
});
