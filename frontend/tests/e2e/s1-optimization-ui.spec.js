import { test, expect } from '@playwright/test';
import { stockKey } from '../../src/features/optimization/runContract.js';
import { api, save, capture, loginApi, setup, login, open, stock, orderStates, run, confirm } from './optimizationRealSupport.js';

const browserErrors = new WeakMap();
test.beforeEach(({ page }) => {
  const errors = []; browserErrors.set(page, errors);
  page.on('pageerror', error => errors.push(error.message));
});
test.afterEach(({ page }, info) => {
  save(info, 'browser-errors.json', browserErrors.get(page));
  expect(browserErrors.get(page)).toEqual([]);
});

test('E2E1 N=1 real: progreso, placements, métricas, confirmación, stock y pedido', async ({ page }, info) => {
  const data = await setup(page, 'single'); await login(page, data.actors.all); await open(page);
  const { result, events } = await run(page, data, info);
  expect(result.completo).toBe(true); expect(result.metrics_available).toBe(true);
  expect(new Set(events.map(e => e.event))).toEqual(new Set(['optimization_started', 'group_started', 'piece_started', 'piece_placed', 'group_completed', 'metrics_calculated', 'optimization_completed']));
  await expect(page.getByRole('heading', { name: 'Resultado First Fit' })).toBeVisible();
  const after = await confirm(page, data, result, info);
  expect(after.sheets[0].cantidad).toBe(0);
  const repeated = await page.request.post(`${api}/api/optimization/runs/${result.id_optimizacion}/confirm`, { headers: data.headers });
  expect(repeated.status()).toBe(409); expect(await stock(page, data)).toEqual(after);
  await page.getByRole('button', { name: 'Registro de pedidos', exact: true }).click();
  const orderRow = page.getByRole('row', { name: new RegExp(`^#${data.orders[0]}\\b`) });
  await expect(orderRow).toContainText('Confirmado');
  await capture(page, info, 'orders-confirmed', orderRow);
  await page.getByRole('button', { name: 'Gestión de inventario', exact: true }).click();
  const history = page.getByRole('button', { name: `Ver historial de plancha #${data.sheets[0]}`, exact: true });
  const sheetRow = page.getByRole('row').filter({ has: history });
  await expect(sheetRow.getByRole('cell').nth(3)).toHaveText('0');
  await expect(sheetRow).toContainText('Inactivo');
  await capture(page, info, 'inventory-updated', sheetRow);
  await history.click();
  const dialog = page.getByRole('dialog', { name: `Historial de movimientos · Plancha #${data.sheets[0]}` });
  await expect(dialog.getByRole('heading', { name: 'Consumo por optimización' })).toBeVisible();
  await capture(page, info, 'inventory-movement', dialog);
});
test('E2E2 multipedido real: una corrida confirma todos', async ({ page }, info) => {
  const data = await setup(page, 'multiple'); await login(page, data.actors.all); await open(page);
  const { result } = await run(page, data, info);
  expect(result.order_ids).toEqual(data.orders);
  expect(new Set(result.placements.map(p => p.id_pedido))).toEqual(new Set(data.orders));
  await confirm(page, data, result, info);
});
test('E2E3 multimaterial real: layouts y métricas separados', async ({ page }, info) => {
  const data = await setup(page, 'multimaterial'); await login(page, data.actors.all); await open(page);
  const { result } = await run(page, data, info);
  expect(result.groups).toHaveLength(2); expect(result.materials_used).toHaveLength(2);
  for (const material of data.materials) {
    await page.getByLabel('Grupo del resultado').selectOption(`${material.id_tipo_vidrio}:${material.espesor_mm}`);
    await expect(page.locator('[data-placement]')).toHaveCount(1);
    await capture(page, info, `material-${material.id_tipo_vidrio}`);
  }
  await confirm(page, data, result, info);
});
test('E2E4 plancha multiunidad real: 3 placements consumen 2 unidades', async ({ page }, info) => {
  const data = await setup(page, 'multiunit'); await login(page, data.actors.all); await open(page);
  const { result } = await run(page, data, info);
  expect(result.placements.map(p => p.unit_index)).toEqual([1, 2, 3]);
  expect(result.materials_used.map(stockKey)).toEqual([`PLANCHA:${data.sheets[0]}:1`, `PLANCHA:${data.sheets[0]}:2`]);
  await expect(page.locator('[data-placement]')).toHaveCount(2);
  await page.getByLabel('Plancha o retazo', { exact: true }).selectOption(`PLANCHA:${data.sheets[0]}:2`);
  await expect(page.locator('[data-placement]')).toHaveCount(1);
  await page.getByRole('button', { name: 'Ver en 3D', exact: true }).click();
  await expect(page.locator('[data-piece-3d]')).toHaveCount(1);
  const slider = page.getByRole('slider', { name: 'Giro horizontal de la vista 3D' });
  await slider.focus(); await page.keyboard.press('End'); await expect(slider).toHaveAttribute('aria-valuenow', '90');
  await capture(page, info, '3d-unit2');
  await page.getByRole('button', { name: 'Ver en 2D', exact: true }).click();
  await page.getByRole('button', { name: 'Acercar 2D', exact: true }).click();
  await expect(page.getByLabel('Ampliación 2D')).toHaveText('150 %');
  const after = await confirm(page, data, result, info); expect(after.sheets[0].cantidad).toBe(2);
});
test('E2E5 retazo primero real: dos piezas consumen un retazo una sola vez', async ({ page }, info) => {
  const data = await setup(page, 'remnant'); await login(page, data.actors.all); await open(page);
  const { result } = await run(page, data, info);
  expect(result.placements.every(p => p.material_source === 'RETAZO' && p.material_id === data.remnants[0])).toBe(true);
  const after = await confirm(page, data, result, info);
  expect(after.remnants[0].estado).toBe(false); expect(after.sheets[0].cantidad).toBe(1);
});
test('E2E6 SIN_SOLUCION real: diagnóstico, pedidos PENDIENTE y stock intacto', async ({ page }, info) => {
  const data = await setup(page, 'incomplete'); await login(page, data.actors.all); await open(page);
  const { result, before } = await run(page, data, info);
  expect(result.estado).toBe('SIN_SOLUCION'); expect(result.completo).toBe(false); expect(result.confirmable).toBe(false);
  expect(result.placements).toHaveLength(1); expect(result.unplaced_units).toHaveLength(1);
  expect(await orderStates(page, data)).toEqual(['PENDIENTE']); expect(await stock(page, data)).toEqual(before);
  save(info, 'stock-after.json', await stock(page, data));
  save(info, 'orders-after.json', { order_ids: data.orders, states: await orderStates(page, data) });
  await expect(page.getByRole('button', { name: 'Confirmar solución', exact: true })).toHaveCount(0);
  await capture(page, info, 'sin-solucion');
});
test('E2E7 409 real: stock cambiado, feedback y ninguna confirmación parcial', async ({ page }, info) => {
  const data = await setup(page, 'conflict'); await login(page, data.actors.all); await open(page);
  const { result } = await run(page, data, info);
  const change = await page.request.patch(`${api}/api/inventory/planchas/${data.sheets[0]}`, { headers: data.headers, data: { cantidad: 0 } });
  expect(change.status()).toBe(200);
  const before = await stock(page, data);
  save(info, 'conflict-stock-before.json', before);
  await page.getByRole('button', { name: 'Confirmar solución', exact: true }).click();
  const post = page.waitForResponse(r => r.url().endsWith(`/runs/${result.id_optimizacion}/confirm`) && r.request().method() === 'POST');
  await page.getByRole('alertdialog').getByRole('button', { name: 'Confirmar solución', exact: true }).click();
  const response = await post; expect(response.status()).toBe(409);
  save(info, 'conflict.json', await response.json());
  await expect(page.getByText(/El inventario cambió \(409\)/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirmar solución', exact: true })).toBeDisabled();
  expect(await orderStates(page, data)).toEqual(['OPTIMIZADO']); expect(await stock(page, data)).toEqual(before);
  save(info, 'conflict-stock-after.json', await stock(page, data));
  save(info, 'orders-after.json', { order_ids: data.orders, states: await orderStates(page, data) });
  const movements = await page.request.get(`${api}/api/inventory/planchas/${data.sheets[0]}/movimientos`, { headers: data.headers });
  expect(movements.status()).toBe(200); expect(await movements.json()).toEqual([]);
  save(info, 'movements.json', await movements.json());
  await capture(page, info, '409');
});
test('E2E8 RBAC real: sin view, view, execute y confirm independientes', async ({ page }, info) => {
  const data = await setup(page, 'rbac');
  await login(page, data.actors.none);
  await expect(page.getByRole('button', { name: 'Optimización', exact: true })).toHaveCount(0);
  const none = await loginApi(page.request, data.actors.none);
  expect((await page.request.get(`${api}/api/optimization/runs/1`, { headers: none })).status()).toBe(403);
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
  await login(page, data.actors.execute); await open(page);
  const { result } = await run(page, data, info);
  await expect(page.getByRole('button', { name: 'Confirmar solución', exact: true })).toHaveCount(0);
  const execute = await loginApi(page.request, data.actors.execute);
  expect((await page.request.post(`${api}/api/optimization/runs/${result.id_optimizacion}/confirm`, { headers: execute })).status()).toBe(403);
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
  await login(page, data.actors.view); await open(page);
  await expect(page.getByRole('button', { name: 'Preparar optimización', exact: true })).toHaveCount(0);
  await page.getByLabel('ID de optimización', { exact: true }).fill(String(result.id_optimizacion));
  await page.getByRole('button', { name: 'Consultar resultado', exact: true }).click();
  await expect(page.getByText('Estado del cálculo: COMPLETADA', { exact: true })).toBeVisible();
  const view = await loginApi(page.request, data.actors.view);
  expect((await page.request.post(`${api}/api/optimization/runs`, { headers: view, data: { order_ids: data.orders } })).status()).toBe(403);
  await capture(page, info, 'view-only');
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
  await login(page, data.actors.confirm); await open(page);
  await page.getByLabel('ID de optimización', { exact: true }).fill(String(result.id_optimizacion));
  await page.getByRole('button', { name: 'Consultar resultado', exact: true }).click();
  await confirm(page, data, result, info);
});
test('E2E9 rotación real: contorno orientado se traduce una sola vez en 2D y 3D', async ({ page }, info) => {
  const data = await setup(page, 'rotated'); await login(page, data.actors.all); await open(page);
  const { result } = await run(page, data, info);
  expect(Number(result.placements[0].rotation_deg)).toBe(90);
  expect(result.placements[0].geometria).toEqual({ type: 'RECTANGULO', width_mm: 40, height_mm: 70 });
  const placed = page.locator('[data-placement]');
  await expect(placed).toHaveAttribute('transform', `translate(${result.placements[0].x_mm} ${result.placements[0].y_mm})`);
  await expect(placed.locator('rect')).toHaveAttribute('width', '40');
  await expect(placed.locator('rect')).toHaveAttribute('height', '70');
  expect(await placed.evaluate(e => e.outerHTML)).not.toContain('rotate(');
  await page.getByRole('button', { name: 'Ver en 3D', exact: true }).click();
  await expect(page.locator('[data-piece-3d]')).toHaveCount(1);
  await capture(page, info, 'oriented-3d');
  await confirm(page, data, result, info);
});

test('E2E10 CA-28 conjunto: dos pedidos, dos materiales, cantidad y unidades físicas reales', async ({ page }, info) => {
  const data = await setup(page, 'combined'); await login(page, data.actors.all); await open(page);
  const { result } = await run(page, data, info);
  expect(result.order_ids).toEqual(data.orders); expect(data.orders).toHaveLength(2);
  expect(result.groups).toHaveLength(2); expect(result.placed_units).toBe(6); expect(result.completo).toBe(true);
  expect(new Set(result.placements.map(p => p.id_pedido))).toEqual(new Set(data.orders));
  expect(result.materials_used.map(stockKey)).toEqual([
    `PLANCHA:${data.sheets[0]}:1`, `PLANCHA:${data.sheets[0]}:2`, `PLANCHA:${data.sheets[1]}:1`,
  ]);
  await page.getByLabel('Plancha o retazo', { exact: true }).selectOption(`PLANCHA:${data.sheets[0]}:2`);
  await expect(page.locator('[data-placement]')).toHaveCount(2);
  const after = await confirm(page, data, result, info);
  expect(after.sheets.map(s => s.cantidad)).toEqual([0, 0]);
});
