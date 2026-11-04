// Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { api, setup, login, loginApi, open, stock, capture, save } from './optimizationRealSupport.js';
import { parseComparisonV2, parseExecutionV2, parseComparisonEventV2 } from '../../src/features/optimization/comparisonV2Contract.js';

test('TA-043 B06 smoke: API publica seis motores, recuperacion y compatibilidad real', async ({ page }, info) => {
  test.setTimeout(90_000);
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  const data = await setup(page, 'single', { createOrders: false });
  const before = await stock(page, data);
  const allInventory = async () => {
    const read = async route => {
      const response = await page.request.get(`${api}/api/inventory/${route}`, { headers: data.headers });
      expect(response.status()).toBe(200); return response.json();
    };
    const sheets = await read('planchas'); const remnants = await read('retazos');
    const movements = await Promise.all([
      ...sheets.map(s => read(`planchas/${s.id_plancha}/movimientos`)),
      ...remnants.map(r => read(`retazos/${r.id_retazo}/movimientos`)),
    ]);
    return { sheets, remnants, movements };
  };
  const allBefore = await allInventory();
  const created = await page.request.post(`${api}/api/orders`, { headers: data.headers, data: { id_cliente: 41, piezas: [
    { ...data.materials[0], tipo_forma: 'RECTANGULO', cantidad: 1, width_mm: 10, height_mm: 10 },
    { ...data.materials[0], tipo_forma: 'CIRCUNFERENCIA', cantidad: 1, radius_mm: 2 },
    { ...data.materials[0], tipo_forma: 'POLIGONO_CONVEXO', cantidad: 1, vertices_mm: [[0, 0], [4, 0], [0, 3]] },
  ] } });
  expect(created.status()).toBe(201); data.orders = [(await created.json()).id_pedido];
  await login(page, data.actors.all, { comparative: true }); await open(page);
  const http = async (path, { method = 'GET', body, key } = {}) => page.evaluate(async args => {
    const response = await fetch(args.url, { method: args.method, headers: args.headers,
      ...(args.body ? { body: JSON.stringify(args.body) } : {}) });
    const text = await response.text();
    return { status: response.status, location: response.headers.get('Location'),
      body: response.headers.get('content-type')?.includes('application/json') ? JSON.parse(text) : text };
  }, { url: `${api}${path}`, method, body,
    headers: { ...data.headers, 'Content-Type': 'application/json', ...(key ? { 'Idempotency-Key': key } : {}) } });
  expect((await http('/health/ready')).status).toBe(200);
  const key = `b06-browser-${info.project.name}`;
  const post = await http('/api/optimization/comparisons-v2', { method: 'POST', body: { order_ids: data.orders }, key });
  expect(post.status).toBe(201);
  const accepted = parseComparisonV2(post.body);
  let current;
  await expect.poll(async () => {
    const response = await http(post.location); expect(response.status).toBe(200);
    current = parseComparisonV2(response.body); return current.terminal;
  }, { timeout: 30_000 }).toBe(true);
  expect(current.methods).toEqual(['FF', 'BF', 'WF', 'HF', 'M5', 'M6-BS']);
  expect(Number(current.configuration.paso_angular_grados)).toBe(5);
  expect(current.executions.every(e => e.complete && e.result_available && e.diagnostic.termination_reason === 'COMPLETED')).toBe(true);
  const results = [];
  for (const execution of current.executions) {
    const result = await http(`${post.location}/executions/${execution.execution_id}`);
    expect(result.status).toBe(200); results.push(parseExecutionV2(result.body, current, execution));
    expect(result.body.result.placed_units).toBe(3); expect(result.body.result.metrics).not.toBeNull();
  }
  const stream = await http(`${post.location}/events`); expect(stream.status).toBe(200);
  const events = stream.body.trim().split('\n').map(line => parseComparisonEventV2(JSON.parse(line), current));
  expect(events.filter(e => e.event === 'result_persisted')).toHaveLength(6);
  expect(events.at(-1).event).toBe('comparison_finished');
  expect((await http('/api/optimization/comparisons-v2/requests/' + key)).body).toEqual(current);
  const replay = await http('/api/optimization/comparisons-v2', { method: 'POST', body: { order_ids: data.orders }, key });
  expect(replay.status).toBe(201); expect(replay.body.comparison_id).toBe(accepted.comparison_id);
  expect((await http(`/api/optimization/comparisons/${current.comparison_id}`)).status).toBe(409);
  await page.reload(); await open(page);
  expect((await http(post.location)).body).toEqual(current);
  expect(await stock(page, data)).toEqual(before);
  expect(await allInventory()).toEqual(allBefore);
  save(info, 'b06-six-results.json', { accepted, current, results, events, runtime: data.runtime,
    inventoryBefore: before, inventoryAfter: await stock(page, data),
    allInventoryBefore: allBefore, allInventoryAfter: await allInventory(),
    visualIntegration: 'PENDING_B07', smokeIntegral: 'PENDING_B09_B11' });
  await capture(page, info, 'b06-current-application');
  const released = await http(`${post.location}/release`, { method: 'POST', body: { expected_version: current.version } });
  expect(released.status).toBe(200); expect(released.body.released).toBe(true);
  // Real existing UI remains FF/BF/WF; no v2 tabs are created by this test.
  await page.reload(); await open(page);
  await page.getByRole('checkbox', { name: new RegExp(`Pedido #${data.orders[0]}\\b`) }).check();
  const v1post = page.waitForResponse(r => new URL(r.url()).pathname === '/api/optimization/comparisons' && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar con los tres motores', exact: true }).click();
  const v1response = await v1post; expect(v1response.status()).toBe(201);
  const v1id = (await v1response.json()).comparison_id;
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  await expect(page.getByRole('tab')).toHaveCount(4);
  const v1 = await http(`/api/optimization/comparisons/${v1id}`);
  expect(v1.body.executions.map(e => e.method)).toEqual(['FF', 'BF', 'WF']);
  const mismatch = await http(`/api/optimization/comparisons-v2/${v1id}`);
  expect(mismatch.status).toBe(409); expect(mismatch.body.detail.code).toBe('COMPARISON_PROFILE_MISMATCH');
  expect((await http('/api/optimization/comparisons-v2', { method: 'POST', body: { order_ids: data.orders }, key: 'browser-conflict-0001' })).status).toBe(409);
  expect((await http('/api/optimization/comparisons-v2/0')).status).toBe(422);
  await page.reload(); await open(page);
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  expect((await http(`/api/optimization/comparisons/${v1id}`)).body).toEqual(v1.body);
  await page.getByRole('button', { name: 'Liberar pedidos sin confirmar', exact: true }).click();
  await expect(page.getByText(new RegExp(`Trabajo #${v1id} liberado sin confirmar`))).toBeVisible();
  const legacy = await http('/api/optimization/runs', { method: 'POST', body: { order_ids: data.orders } });
  expect(legacy.status).toBe(201);
  const lines = legacy.body.trim().split('\n').map(JSON.parse);
  expect(lines.at(-1).event).toBe('optimization_completed');
  const ff = await http(`/api/optimization/runs/${lines[0].id_optimizacion}`);
  expect(ff.status).toBe(200); expect(ff.body.metodo).toBe('FF'); expect(ff.body.completo).toBe(true);
  expect(await stock(page, data)).toEqual(before); expect(errors).toEqual([]);
  expect(await allInventory()).toEqual(allBefore);
  save(info, 'b06-history-legacy.json', { v1: v1.body, legacy: ff.body, mismatch, cleanup: 'HARNESS_OWNED_SERVICES' });
});

test('TA-043 B02 smoke: historia v1 y FF intacta después del upgrade PostgreSQL', async ({ page }, info) => {
  const backend = fileURLToPath(new URL('../../../backend/', import.meta.url));
  const migrate = (...args) => JSON.parse(execFileSync('python', ['-m', 'tests.optimization_b02_upgrade', ...args],
    { cwd: backend, encoding: 'utf8' }));
  expect(migrate('--prepare').prepared_revision).toBe('s2cmp01a1b2c');
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  const data = await setup(page, 'single');
  const inventory = await stock(page, data);
  await login(page, data.actors.all, { comparative: true }); await open(page);
  await page.getByRole('checkbox', { name: new RegExp(`Pedido #${data.orders[0]}\\b`) }).check();
  const accepted = page.waitForResponse(r => new URL(r.url()).pathname === '/api/optimization/comparisons'
    && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar con los tres motores', exact: true }).click();
  const response = await accepted; expect(response.status()).toBe(201);
  const id = (await response.json()).comparison_id;
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  const get = async url => {
    const result = await page.request.get(`${api}/api/optimization/${url}`, { headers: data.headers });
    expect(result.status()).toBe(200); return result.json();
  };
  const current = await get(`comparisons/${id}`);
  expect(current.executions.map(e => e.method)).toEqual(['FF', 'BF', 'WF']);
  const results = await Promise.all(current.executions.map(e => get(`comparisons/${id}/executions/${e.execution_id}`)));
  const order = await page.request.post(`${api}/api/orders`, { headers: data.headers,
    data: { id_cliente: 41, piezas: [{ ...data.materials[0], tipo_forma: 'RECTANGULO', cantidad: 1, width_mm: 10, height_mm: 10 }] } });
  expect(order.status()).toBe(201);
  const legacy = await page.request.post(`${api}/api/optimization/runs`, { headers: data.headers,
    data: { order_ids: [(await order.json()).id_pedido] } });
  expect(legacy.status()).toBe(201);
  const lines = (await legacy.text()).trim().split('\n').map(JSON.parse);
  expect(lines.at(-1).event).toBe('optimization_completed');
  const runId = lines[0].id_optimizacion;
  const ff = await get(`runs/${runId}`); expect(ff.metodo).toBe('FF'); expect(ff.completo).toBe(true);
  const migration = migrate();
  expect(migration.result).toBe('PASS');
  expect(migration.before_sha256).toEqual(migration.after_sha256);
  expect(await get(`comparisons/${id}`)).toEqual(current);
  for (let i = 0; i < results.length; i++) {
    expect(await get(`comparisons/${id}/executions/${current.executions[i].execution_id}`)).toEqual(results[i]);
  }
  expect(await get(`runs/${runId}`)).toEqual(ff);
  await page.reload(); await open(page);
  // Let the existing automatic recovery settle before testing explicit lookup.
  await expect(page.getByRole('tab')).toHaveCount(4);
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  await page.getByLabel('Consultar trabajo guardado').fill(String(id));
  await page.getByRole('button', { name: 'Consultar', exact: true }).click();
  await expect(page.getByRole('tab')).toHaveCount(4);
  for (const name of ['First Fit', 'Best Fit', 'Worst Fit']) {
    await page.getByRole('tab', { name: new RegExp(name) }).click();
    const panel = page.getByRole('tabpanel', { name: new RegExp(name) });
    await expect(panel).toBeVisible();
    await panel.getByRole('button', { name: /Resultado/ }).click();
    await expect(panel.locator('[data-placement]')).toHaveCount(1);
    await capture(page, info, `b02-history-${name.replaceAll(' ', '-')}`, panel);
  }
  expect(await stock(page, data)).toEqual(inventory);
  expect(errors).toEqual([]);
  save(info, 'b02-migration.json', migration);
  save(info, 'b02-historical-comparison.json', { before: current, after: await get(`comparisons/${id}`), results });
  save(info, 'b02-historical-ff.json', { before: ff, after: await get(`runs/${runId}`) });
});

test('TA-043 B01 smoke: arranque real, comparison-v1 y runs legacy sin consumir stock', async ({ page }, info) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const openapi = await page.request.get(`${api}/openapi.json`);
  expect(openapi.status()).toBe(200);
  const paths = (await openapi.json()).paths;
  expect(paths['/api/optimization/comparisons']).toBeTruthy();
  expect(paths['/api/optimization/runs']).toBeTruthy();
  // B06 publishes v2 explicitly; existing v1/legacy behavior below stays intact.
  expect(paths['/api/optimization/comparisons-v2']).toBeTruthy();
  const data = await setup(page, 'single');
  const before = await stock(page, data);
  await login(page, data.actors.all, { comparative: true }); await open(page);
  await page.getByRole('checkbox', { name: new RegExp(`Pedido #${data.orders[0]}\\b`) }).check();
  const accepted = page.waitForResponse(r => new URL(r.url()).pathname === '/api/optimization/comparisons'
    && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Comparar con los tres motores', exact: true }).click();
  const response = await accepted;
  expect(response.status()).toBe(201);
  const comparison = await response.json();
  expect(comparison.profile).toBe('comparison-v1');
  expect(comparison.executions.map(e => e.method)).toEqual(['FF', 'BF', 'WF']);
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  await expect(page.getByRole('tab')).toHaveCount(4);
  const current = await (await page.request.get(`${api}/api/optimization/comparisons/${comparison.comparison_id}`,
    { headers: data.headers })).json();
  expect(current.terminal).toBe(true);
  for (const execution of current.executions) {
    const own = await page.request.get(`${api}/api/optimization/comparisons/${current.comparison_id}/executions/${execution.execution_id}`,
      { headers: data.headers });
    expect(own.status()).toBe(200);
    expect((await own.json()).result.metodo).toBe(execution.method);
    expect(execution.complete).toBe(true);
  }
  expect(await stock(page, data)).toEqual(before);
  save(info, 'b01-comparison-v1.json', current);
  await capture(page, info, 'b01-comparison-v1');
  await page.getByRole('button', { name: 'Liberar pedidos sin confirmar', exact: true }).click();
  await expect(page.getByText(new RegExp(`Trabajo #${current.comparison_id} liberado sin confirmar`))).toBeVisible();
  await page.goto('/first-fit-compatibility.html'); await open(page);
  await page.getByRole('checkbox', { name: new RegExp(`^#${data.orders[0]} ·`) }).check();
  await page.getByRole('button', { name: 'Revisar vidrios y piezas', exact: true }).click();
  const post = page.waitForResponse(r => new URL(r.url()).pathname === '/api/optimization/runs' && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Calcular distribución', exact: true }).click();
  const legacy = await post;
  expect(legacy.status()).toBe(201);
  const lines = (await legacy.text()).trim().split('\n').map(line => JSON.parse(line));
  expect(lines.at(-1).event).toBe('optimization_completed');
  const runId = lines[0].id_optimizacion;
  const result = await page.request.get(`${api}/api/optimization/runs/${runId}`, { headers: data.headers });
  expect(result.status()).toBe(200);
  const ff = await result.json();
  expect(ff.metodo).toBe('FF'); expect(ff.completo).toBe(true);
  await expect(page.getByRole('heading', { name: 'Resultado del corte' })).toBeVisible();
  expect(await stock(page, data)).toEqual(before);
  save(info, 'b01-runs-legacy.json', ff);
  await capture(page, info, 'b01-runs-legacy');
  expect(errors).toEqual([]);
});

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
