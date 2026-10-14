import { test, expect } from '@playwright/test';

const apiOrigin = 'http://127.0.0.1:8017';
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

async function rectangle(page) {
  await page.getByRole('button', { name: 'Agregar pieza', exact: true }).click();
  await page.getByLabel('Material', { exact: true }).selectOption('7');
  await page.getByLabel('Espesor', { exact: true }).selectOption('6');
  await page.getByLabel('Ancho (mm)', { exact: true }).fill('100');
  await page.getByLabel('Alto (mm)', { exact: true }).fill('200');
}

test('T03: alta contextual, bloqueo sin cliente, persistencia y lectura real', async ({ page }) => {
  await rectangle(page);
  await expect(page.getByRole('button', { name: 'Guardar pedido' })).toBeDisabled();
  await page.getByRole('button', { name: 'Registrar nuevo cliente' }).click();
  await page.getByLabel('Nombre o razón social', { exact: true }).fill('Cliente nuevo E2E');
  const created = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/clients` && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Registrar y seleccionar' }).click();
  const clientResponse = await created;
  expect(clientResponse.status()).toBe(201);
  const client = await clientResponse.json();
  await expect(page.getByLabel('Cliente seleccionado', { exact: true })).toContainText(client.nombre_razon_social);
  const saved = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/orders` && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Guardar pedido' }).click();
  const response = await saved;
  expect(response.status()).toBe(201);
  const order = await response.json();
  expect(order.id_cliente).toBe(client.id_cliente);
  expect(response.request().postDataJSON().id_cliente).toBe(client.id_cliente);
  await expect(page.getByText(`Pedido registrado correctamente. ID del pedido: ${order.id_pedido}.`)).toBeVisible();
  const headers = { Authorization: response.request().headers().authorization };
  const read = await page.request.get(`${apiOrigin}/api/orders/${order.id_pedido}`, { headers });
  expect(read.status()).toBe(200);
  const persisted = await read.json();
  expect(persisted.id_cliente).toBe(client.id_cliente);
  expect(persisted.id_usuario_registro).not.toBe(client.id_cliente);
  expect(persisted.piezas[0]).toMatchObject({ cantidad: 1, id_tipo_vidrio: 7, dimensiones: { width_mm: 100, height_mm: 200 } });
  const invalid = await page.request.post(`${apiOrigin}/api/orders`, {
    headers, data: { ...response.request().postDataJSON(), id_cliente: 2147483647 },
  });
  expect(invalid.status()).toBe(422);
  expect((await invalid.json()).detail).toContain('no existe');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('T03: duplicado controlado, búsqueda documental y cambio a cliente inactivo', async ({ page }) => {
  await page.getByRole('button', { name: 'Registrar nuevo cliente' }).click();
  await page.getByLabel('Nombre o razón social', { exact: true }).fill('Duplicado de prueba');
  await page.getByLabel('Tipo de documento (opcional)').fill('TEST');
  await page.getByLabel('Número de documento (opcional)').fill('DEMO-003');
  await page.getByRole('button', { name: 'Registrar y seleccionar' }).click();
  await expect(page.getByRole('alert')).toContainText('Ya existe un cliente');
  await expect(page.getByLabel('Nombre o razón social', { exact: true })).toHaveValue('Duplicado de prueba');
  await page.getByRole('button', { name: 'Volver a buscar' }).click();
  await page.getByLabel('Buscar por', { exact: true }).selectOption('document');
  await page.getByLabel('Documento del cliente').fill('DEMO-003');
  await page.getByRole('button', { name: 'Buscar', exact: true }).click();
  await page.getByRole('button', { name: 'Seleccionar Vidrios Norte' }).click();
  await rectangle(page);
  await page.getByRole('button', { name: 'Cambiar cliente' }).click();
  await expect(page.getByRole('button', { name: 'Guardar pedido' })).toBeDisabled();
  await page.getByLabel('Documento del cliente').fill('DEMO-004');
  await page.getByRole('button', { name: 'Buscar', exact: true }).click();
  await page.getByRole('button', { name: 'Seleccionar Cliente inactivo' }).click();
  await expect(page.getByLabel('Cliente seleccionado', { exact: true })).toContainText('Inactivo');
  await expect(page.getByText('Pieza 1', { exact: true })).toBeVisible();
  const saved = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/orders` && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Guardar pedido' }).click();
  const response = await saved;
  expect(response.status()).toBe(201);
  expect((await response.json()).id_cliente).toBe(42);
});
