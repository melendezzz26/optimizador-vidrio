// HU-018 T05: archivo con filas observadas -> corrección -> revalidación -> agregar al pedido -> registrar.
import { Buffer } from 'node:buffer';
import { test, expect } from '@playwright/test';

const apiOrigin = 'http://127.0.0.1:8017';
const CSV = [
  'tipo,cantidad,medidas',
  'R,3,800,600',
  'C,2,150',
  'P,1,{{300,},{400,},{500,}}',
  'C,0,150',
].join('\n');

test.beforeEach(async ({ page, baseURL }) => {
  await page.route('**/*', (route) => [baseURL, apiOrigin].includes(new URL(route.request().url()).origin)
    ? route.continue() : route.abort());
  await page.goto('/');
  await page.getByLabel('Usuario', { exact: true }).fill('O70000001');
  await page.getByLabel('Contraseña', { exact: true }).fill('Orders-test-2026!');
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Inicio', exact: true })).toHaveAttribute('aria-current', 'page');
  await page.getByRole('button', { name: 'Registro de pedidos', exact: true }).click();
  await page.getByRole('button', { name: 'Nuevo pedido', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Crear pedido', exact: true })).toBeVisible();
});

test('importación con corrección: el pedido queda con exactamente las piezas del archivo', async ({ page }) => {
  const orderPosts = [];
  page.on('request', (request) => {
    if (request.url() === `${apiOrigin}/api/orders` && request.method() === 'POST') orderPosts.push(request);
  });
  await page.getByLabel('Nombre del cliente').fill('Vidrios Norte');
  await page.getByRole('button', { name: 'Buscar', exact: true }).click();
  await page.getByRole('button', { name: 'Seleccionar Vidrios Norte' }).click();

  await page.getByRole('button', { name: 'Importar CSV/XLSX' }).click();
  const panel = page.getByRole('region', { name: 'Importar piezas desde archivo' });
  await panel.getByLabel('Archivo CSV o XLSX').setInputFiles({ name: 'piezas.csv', mimeType: 'text/csv', buffer: Buffer.from(CSV) });
  await expect(panel.getByText('4 filas · 3 válidas · 1 observadas')).toBeVisible();
  await expect(panel.getByRole('row', { name: /^5 Círculo/ })).toContainText('Cantidad debe ser un entero mayor a 0');

  const add = panel.getByRole('button', { name: 'Agregar al pedido' });
  await panel.getByLabel('Tipo de vidrio para estas piezas').selectOption('7');
  await panel.getByLabel('Espesor (mm)').selectOption('6');
  await expect(add).toBeDisabled();
  await expect(panel.getByText('Corrige 1 fila observada para continuar.')).toBeVisible();

  await panel.getByLabel('Fila 5').fill('C,1,150');
  const revalidated = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/orders/import/validate`);
  await panel.getByRole('button', { name: 'Revalidar' }).click();
  expect((await revalidated).status()).toBe(200);
  await expect(panel.getByText('4 filas · 4 válidas · 0 observadas')).toBeVisible();
  await expect(add).toBeEnabled();
  expect(orderPosts).toHaveLength(0);

  await add.click();
  await expect(panel).toHaveCount(0);
  await expect(page.getByText('Se agregaron 4 piezas del archivo al pedido.')).toBeVisible();
  await expect(page.locator('.orders-material-group')).toHaveCount(1);

  const saved = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/orders` && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Guardar pedido' }).dblclick();
  const response = await saved;
  expect(response.status()).toBe(201);
  const { id_pedido } = await response.json();
  await expect(page.getByText(`Pedido registrado correctamente. ID del pedido: ${id_pedido}.`)).toBeVisible();
  expect(orderPosts).toHaveLength(1);
  expect(response.request().postDataJSON().piezas.map(({ tipo_forma, cantidad, id_tipo_vidrio, espesor_mm }) =>
    [tipo_forma, cantidad, id_tipo_vidrio, espesor_mm])).toEqual([
    ['RECTANGULO', 3, 7, 6], ['CIRCUNFERENCIA', 2, 7, 6], ['POLIGONO_CONVEXO', 1, 7, 6], ['CIRCUNFERENCIA', 1, 7, 6],
  ]);

  const headers = { Authorization: response.request().headers().authorization };
  const persisted = await (await page.request.get(`${apiOrigin}/api/orders/${id_pedido}`, { headers })).json();
  expect(persisted.piezas.map(piece => [piece.tipo_forma, piece.cantidad])).toEqual([
    ['RECTANGULO', 3], ['CIRCUNFERENCIA', 2], ['POLIGONO_CONVEXO', 1], ['CIRCUNFERENCIA', 1],
  ]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('un archivo no admitido muestra el error sin registrar nada', async ({ page }) => {
  await page.getByRole('button', { name: 'Importar CSV/XLSX' }).click();
  const panel = page.getByRole('region', { name: 'Importar piezas desde archivo' });
  const answered = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/orders/import/preview`);
  await panel.getByLabel('Archivo CSV o XLSX').setInputFiles({ name: 'piezas.txt', mimeType: 'text/plain', buffer: Buffer.from('R,1,10,10') });
  const response = await answered;
  expect(response.status()).toBe(422);
  await expect(panel.getByRole('alert')).toContainText('Selecciona un archivo .csv o .xlsx.');
  await expect(panel.getByRole('table')).toHaveCount(0);
});

test('una observación bloquea guardar piezas manuales hasta corregirla', async ({ page }) => {
  await page.getByLabel('Nombre del cliente').fill('Vidrios Norte');
  await page.getByRole('button', { name: 'Buscar', exact: true }).click();
  await page.getByRole('button', { name: 'Seleccionar Vidrios Norte' }).click();
  const group = page.locator('.orders-material-group').first();
  await group.getByLabel('Tipo de vidrio', { exact: true }).selectOption('7');
  await group.getByLabel('Espesor del vidrio (mm)').selectOption('6');
  await group.getByLabel('Ancho (mm)').fill('800');
  await group.getByLabel('Alto (mm)').fill('600');
  const save = page.getByRole('button', { name: 'Guardar pedido' });
  await expect(save).toBeEnabled();
  await page.getByRole('button', { name: 'Importar CSV/XLSX' }).click();
  const panel = page.getByRole('region', { name: 'Importar piezas desde archivo' });
  await panel.getByLabel('Archivo CSV o XLSX').setInputFiles({ name: 'piezas.csv', mimeType: 'text/csv', buffer: Buffer.from('DESCONOCIDO\nR,1,100,200') });
  await expect(panel.getByLabel('Fila 1')).toBeVisible();
  await expect(save).toBeDisabled();
  await expect(page.getByText('Corrige las filas observadas antes de confirmar el pedido.')).toBeVisible();
  await panel.getByLabel('Fila 1').fill('C,1,150');
  await panel.getByRole('button', { name: 'Revalidar' }).click();
  await expect(panel.getByText('2 filas · 2 válidas · 0 observadas')).toBeVisible();
  await expect(save).toBeEnabled();
});
