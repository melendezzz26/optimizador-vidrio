// TA-046 T03: un pedido con rectángulo y polígono se registra solo con teclado (SPEC-TA-046 CA-07).
import { test, expect } from '@playwright/test';

const apiOrigin = 'http://127.0.0.1:8017';
const press = async (locator, key = 'Enter') => { await locator.focus(); await locator.press(key); };

test.beforeEach(async ({ page, baseURL }) => {
  await page.route('**/*', (route) => [baseURL, apiOrigin].includes(new URL(route.request().url()).origin)
    ? route.continue() : route.abort());
  await page.goto('/');
  await page.getByLabel('Usuario', { exact: true }).fill('O70000001');
  await page.getByLabel('Contraseña', { exact: true }).fill('Orders-test-2026!');
  await page.getByLabel('Contraseña', { exact: true }).press('Enter');
  await expect(page.getByRole('button', { name: 'Inicio', exact: true })).toHaveAttribute('aria-current', 'page');
});

test('registro de pedido completo solo con teclado, sin mouse', async ({ page }) => {
  await press(page.getByRole('button', { name: 'Registro de pedidos', exact: true }));
  await press(page.getByRole('button', { name: 'Nuevo pedido', exact: true }));
  const dialog = page.getByRole('dialog', { name: 'Crear pedido', exact: true });
  await expect(dialog).toBeVisible();

  const client = page.getByLabel('Nombre del cliente');
  await client.fill('Vidrios Norte');
  await client.press('Enter');
  await press(page.getByRole('button', { name: 'Seleccionar Vidrios Norte' }));

  await page.getByLabel('Tipo de vidrio', { exact: true }).selectOption('7');
  await page.getByLabel('Espesor del vidrio (mm)', { exact: true }).selectOption('6');
  await page.getByLabel('Ancho (mm)').fill('800');
  await page.getByLabel('Alto (mm)').fill('600');

  await press(page.getByRole('button', { name: 'Agregar pieza' }));
  const shapes = page.getByLabel('Forma', { exact: true });
  await expect(shapes.nth(1)).toBeFocused();
  await shapes.nth(1).selectOption('POLIGONO_CONVEXO');

  const editor = page.getByRole('dialog', { name: 'Dibujar Polígono Convexo' });
  const sides = editor.getByLabel(/Número de lados/);
  await sides.fill('3');
  await sides.press('Enter');
  const lengths = editor.getByLabel(/Longitud del segmento S\d en milímetros/);
  await expect(lengths.first()).toBeFocused();
  for (const [index, value] of ['300', '400', '500'].entries()) await lengths.nth(index).fill(value);
  const addPolygon = editor.getByRole('button', { name: /Agregar pieza al pedido/ });
  await expect(addPolygon).toBeEnabled();
  await press(addPolygon);
  await expect(editor).toHaveCount(0);
  await expect(page.getByText('✓ Figura configurada')).toBeVisible();

  const saved = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/orders` && response.request().method() === 'POST');
  await press(page.getByLabel('Cantidad', { exact: true }).last());
  const response = await saved;
  expect(response.status()).toBe(201);
  const { piezas } = response.request().postDataJSON();
  expect(piezas.map(({ tipo_forma, cantidad }) => [tipo_forma, cantidad])).toEqual([['RECTANGULO', 1], ['POLIGONO_CONVEXO', 1]]);
  expect(piezas[1].vertices_mm).toHaveLength(3);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('al eliminar un vidrio el foco sigue en el diálogo y Escape lo cierra', async ({ page }) => {
  await press(page.getByRole('button', { name: 'Registro de pedidos', exact: true }));
  await press(page.getByRole('button', { name: 'Nuevo pedido', exact: true }));
  const dialog = page.getByRole('dialog', { name: 'Crear pedido', exact: true });
  const client = page.getByLabel('Nombre del cliente');
  await client.fill('Vidrios Norte');
  await client.press('Enter');
  await press(page.getByRole('button', { name: 'Seleccionar Vidrios Norte' }));
  await press(page.getByRole('button', { name: 'Agregar otro vidrio' }));
  await expect(page.locator('.orders-material-group').nth(1).getByLabel('Tipo de vidrio', { exact: true })).toBeFocused();
  await press(page.getByRole('button', { name: 'Eliminar vidrio' }).last());
  expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
});