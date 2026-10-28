import { calculationState } from '../../src/features/optimization/workLabels.js';
import { expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { parseRun, readNdjson } from '../../src/features/optimization/runContract.js';
import { readVisualNdjson } from '../../src/features/optimization/visualContract.js';

const backend = fileURLToPath(new URL('../../../backend/', import.meta.url));
// Historical evidence is exported only when explicitly requested.
const evidence = process.env.NEWGLASS_OPTIMIZATION_EVIDENCE_DIR;
export const api = 'http://127.0.0.1:8017';
const prefix = info => info.title.split(' ')[0].replace(/[^A-Za-z0-9_-]/g, '');
export const save = (info, name, value) => {
  const directory = evidence ? path.join(evidence, info.project.name) : info.outputPath();
  mkdirSync(directory, { recursive: true });
  writeFileSync(path.join(directory, `${prefix(info)}-${name}`), typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n');
};
export async function capture(page, info, name, target = page) {
  const directory = evidence ? path.join(evidence, info.project.name) : info.outputPath();
  mkdirSync(directory, { recursive: true });
  await target.screenshot({ path: path.join(directory, `${prefix(info)}-${name}.png`), animations: 'disabled' });
}
export async function loginApi(request, credentials) {
  const response = await request.post(`${api}/api/auth/login`, { data: credentials });
  expect(response.status()).toBe(200);
  return { Authorization: `Bearer ${(await response.json()).access_token}` };
}
export async function setup(page, scenario, { createOrders = true } = {}) {
  const data = JSON.parse(execFileSync('python', ['-m', 'tests.optimization_e2e_data', scenario], { cwd: backend, encoding: 'utf8' }));
  const headers = await loginApi(page.request, data.actors.all);
  const rectangle = (material, cantidad = 1, width_mm = 50, height_mm = 50) => ({
    ...material, tipo_forma: 'RECTANGULO', cantidad, width_mm, height_mm,
  });
  const orders = [];
  const pieces = scenario === 'rotated' ? [rectangle(data.materials[0], 1, 70, 40)]
    : scenario === 'combined' ? [rectangle(data.materials[0], 2), rectangle(data.materials[1])]
    : scenario === 'multimaterial' ? data.materials.map(m => rectangle(m))
      : [rectangle(data.materials[0], scenario === 'multiunit' ? 3 : ['remnant', 'incomplete'].includes(scenario) ? 2 : 1)];
  for (let i = 0; i < (createOrders ? (['multiple', 'combined'].includes(scenario) ? 2 : 1) : 0); i++) {
    const response = await page.request.post(`${api}/api/orders`, { headers, data: { id_cliente: 41, piezas: pieces } });
    expect(response.status()).toBe(201);
    orders.push((await response.json()).id_pedido);
  }
  return { ...data, headers, orders };
}
export async function login(page, credentials) {
  await page.goto('/');
  await page.getByLabel('Usuario', { exact: true }).fill(credentials.username);
  await page.getByLabel('Contraseña', { exact: true }).fill(credentials.password);
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Cerrar sesión', exact: true })).toBeVisible();
}
export async function open(page) {
  await page.getByRole('button', { name: 'Optimización', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Optimización de corte', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Explorar demostración' })).toHaveCount(0);
}
export async function stock(page, data) {
  const sheets = await page.request.get(`${api}/api/inventory/planchas`, { headers: data.headers });
  const remnants = await page.request.get(`${api}/api/inventory/retazos`, { headers: data.headers });
  expect(sheets.status()).toBe(200); expect(remnants.status()).toBe(200);
  return {
    sheets: (await sheets.json()).filter(s => data.sheets.includes(s.id_plancha)),
    remnants: (await remnants.json()).filter(r => data.remnants.includes(r.id_retazo)),
  };
}
export async function orderStates(page, data) {
  return Promise.all(data.orders.map(async id => {
    const response = await page.request.get(`${api}/api/orders/${id}`, { headers: data.headers });
    expect(response.status()).toBe(200); return (await response.json()).estado;
  }));
}
export async function run(page, data, info) {
  save(info, 'runtime.json', data.runtime);
  const before = await stock(page, data);
  for (const id of data.orders) await page.getByRole('checkbox', { name: new RegExp(`^#${id} ·`) }).check();
  await capture(page, info, 'selection');
  await page.getByRole('button', { name: 'Revisar vidrios y piezas', exact: true }).click();
  const post = page.waitForResponse(r => new URL(r.url()).pathname === '/api/optimization/runs' && r.request().method() === 'POST');
  const get = page.waitForResponse(r => /^\/api\/optimization\/runs\/\d+$/.test(new URL(r.url()).pathname) && r.request().method() === 'GET');
  await page.getByRole('button', { name: 'Calcular distribución', exact: true }).click();
  const response = await post;
  expect(response.status()).toBe(201);
  expect(response.headers()['content-type']).toContain('application/x-ndjson');
  expect(response.request().postDataJSON()).toEqual({ order_ids: data.orders });
  const wire = await response.text();
  save(info, 'stream.ndjson', wire);
  // Reparse real HTTP bytes with UTF-8 and lines deliberately split. No network fixture.
  const bytes = new TextEncoder().encode(wire);
  async function* fragments() { for (let i = 0; i < bytes.length; i += 7) yield bytes.slice(i, i + 7); }
  const events = [];
  const visual = new URL(response.url()).searchParams.get('stream_profile') === 'visual-v2';
  for await (const event of (visual ? readVisualNdjson : readNdjson)(fragments())) events.push(event);
  expect(events.map(e => e.sequence)).toEqual(events.map((_, i) => i + 1));
  expect(events[0].event).toBe('optimization_started');
  expect(events.at(-1).event).toBe('optimization_completed');
  expect(events.some(e => e.event === 'piece_placed')).toBe(true);
  const canonical = await get;
  expect(canonical.status()).toBe(200);
  const result = parseRun(await canonical.json());
  save(info, 'result.json', result); save(info, 'stock-before.json', before);
  expect(await stock(page, data)).toEqual(before);
  await expect(page.getByText(`Estado del trabajo: ${calculationState(result.estado)}`, { exact: true })).toBeVisible();
  await expect(page.getByText(`${result.placed_units} / ${result.total_units} piezas colocadas`, { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await capture(page, info, 'placements', page.getByRole('region', { name: 'Distribución de piezas', exact: true }));
  await capture(page, info, 'progress-final', page.getByRole('list', { name: 'Etapas de optimización' }));
  if (result.metrics_available) await capture(page, info, 'metrics', page.getByRole('region', { name: 'Resultado del corte', exact: true }));
  return { result, before, events };
}
export async function confirm(page, data, result, info) {
  await page.getByRole('button', { name: 'Confirmar corte', exact: true }).click();
  const dialog = page.getByRole('alertdialog');
  await expect(dialog).toContainText('Se descontarán del inventario');
  await capture(page, info, 'confirmation');
  const post = page.waitForResponse(r => r.url() === `${api}/api/optimization/runs/${result.id_optimizacion}/confirm` && r.request().method() === 'POST');
  await dialog.getByRole('button', { name: 'Confirmar corte', exact: true }).click();
  const response = await post;
  expect(response.status()).toBe(200); expect(response.request().postData()).toBeNull();
  save(info, 'confirmation.json', await response.json());
  await expect(page.getByText('Corte ya confirmado.', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirmar corte', exact: true })).toHaveCount(0);
  const canonical = await page.request.get(`${api}/api/optimization/runs/${result.id_optimizacion}`, { headers: data.headers });
  const dto = parseRun(await canonical.json());
  expect(dto.confirmed).toBe(true); expect(dto.confirmable).toBe(false);
  expect(await orderStates(page, data)).toEqual(data.orders.map(() => 'CONFIRMADO'));
  const after = await stock(page, data);
  expect(after.sheets.every(s => s.cantidad >= 0)).toBe(true);
  save(info, 'stock-after.json', after); save(info, 'confirmed-result.json', dto);
  save(info, 'orders-after.json', { order_ids: data.orders, states: await orderStates(page, data) });
  const movements = [];
  for (const [resource, ids] of [['planchas', data.sheets], ['retazos', data.remnants]]) {
    for (const id of ids) {
      const response = await page.request.get(`${api}/api/inventory/${resource}/${id}/movimientos`, { headers: data.headers });
      expect(response.status()).toBe(200);
      movements.push(...await response.json());
    }
  }
  expect(movements.every(m => m.id_optimizacion === result.id_optimizacion && m.tipo_evento === 'CONSUMO_OPTIMIZACION')).toBe(true);
  save(info, 'movements.json', movements);
  await capture(page, info, 'confirmed');
  return after;
}
