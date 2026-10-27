import { test, expect } from '@playwright/test';
import { setup, login, open, run, stock, orderStates } from './optimizationRealSupport.js';

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

  // The shared helper exercises the canonical V1 POST/GET without legacy preview.
  const { result } = await run(page, data, info);
  expect(result.completo).toBe(true);
  expect(result.metodo).toBe('FF');
  expect(posts).toEqual(['/api/optimization/runs']);
  expect(await stock(page, data)).toEqual(before);
  const stages = page.getByRole('list', { name: 'Etapas de optimización' });
  await expect(stages.getByText('Sin detalle disponible', { exact: true })).toHaveCount(2);
  await expect(stages).toContainText('Resultado completo');
  await expect(page.getByRole('button', { name: 'Confirmar corte', exact: true })).toBeEnabled();
});

test('HU-017 T01: SIN_SOLUCION conserva resultado parcial sin certificar etapas no observadas', async ({ page }, info) => {
  const data = await setup(page, 'incomplete');
  await login(page, data.actors.all); await open(page);
  const { result, before } = await run(page, data, info);
  expect(result.estado).toBe('SIN_SOLUCION');
  const stages = page.getByRole('list', { name: 'Etapas de optimización' });
  await expect(stages).toContainText('Resultado parcial');
  await expect(stages.getByText('Sin detalle disponible', { exact: true })).toHaveCount(2);
  await expect(page.getByRole('button', { name: 'Confirmar corte', exact: true })).toHaveCount(0);
  expect(await stock(page, data)).toEqual(before);
  expect(await orderStates(page, data)).toEqual(['PENDIENTE']);
});
