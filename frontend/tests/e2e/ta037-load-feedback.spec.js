// TA-037 T04: trabajo demasiado grande, con backend y PostgreSQL reales (CA-11).
import { test, expect } from '@playwright/test';
import { api, capture, setup, login, open, stock, orderStates } from './optimizationRealSupport.js';

test('TA037 pedido sobre el límite: aviso comprensible, selección conservada, pedido pendiente y stock intacto', async ({ page }, info) => {
  const data = await setup(page, 'single', { createOrders: false });
  const pieces = [{ ...data.materials[0], tipo_forma: 'RECTANGULO', cantidad: 151, width_mm: 50, height_mm: 50 }];
  const created = await page.request.post(`${api}/api/orders`, { headers: data.headers, data: { id_cliente: 41, piezas: pieces } });
  expect(created.status()).toBe(201);
  data.orders.push((await created.json()).id_pedido);
  const before = await stock(page, data);

  await login(page, data.actors.all); await open(page);
  const order = page.getByRole('checkbox', { name: new RegExp(`^#${data.orders[0]} ·`) });
  await order.check();
  await page.getByRole('button', { name: 'Revisar vidrios y piezas', exact: true }).click();
  const runResponse = page.waitForResponse(r => {
    const url = new URL(r.url());
    return url.origin === api && url.pathname === '/api/optimization/runs' && r.request().method() === 'POST';
  });
  await page.getByRole('button', { name: 'Calcular distribución', exact: true }).click();
  const response = await runResponse;
  expect(new URL(response.url()).searchParams.get('stream_profile')).toBe('visual-v2');
  expect(response.request().postDataJSON()).toEqual({ order_ids: data.orders });
  expect(response.status()).toBe(422);
  expect((await response.json()).detail).toMatchObject({ code: 'LOAD_LIMIT_EXCEEDED', limit: { name: 'units_per_run', maximum: 150, actual: 151 } });

  const notice = page.locator('[data-error-kind="load_limit"]');
  await expect(notice).toBeFocused();
  await expect(notice).toContainText('El trabajo es demasiado grande para un solo cálculo');
  await expect(notice).toContainText('suman 151 unidades y el máximo por cálculo es 150');
  await expect(notice).toContainText('Los pedidos siguen pendientes y no se usó inventario');
  await expect(order).toBeChecked();
  await expect(page.getByRole('button', { name: 'Calcular distribución', exact: true })).toBeEnabled();
  await expect(page.getByRole('heading', { name: 'Progreso de optimización' })).toHaveCount(0);
  await capture(page, info, 'aviso-limite', notice);

  expect(await orderStates(page, data)).toEqual(['PENDIENTE']);
  expect(await stock(page, data)).toEqual(before);
});
