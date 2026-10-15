import { test, expect } from '@playwright/test';
const evidence = '../docs/evidence/sprint-01/S1-OPT-UI';
async function login(page) {
  const user = { id_usuario: 1, username: 'O12345678', nombre: 'Operario de ejemplo', rol: 'Operario' };
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (route.request().method() !== 'GET' && path !== '/api/auth/login') throw new Error('Unexpected mutation: ' + path);
    const data = path === '/api/auth/login' ? { access_token: 'fixture-only', token_type: 'bearer', usuario: user }
      : path === '/api/auth/me' ? user : path === '/api/orders' ? { items: [], total: 0, total_pages: 0 } : [];
    await route.fulfill({ json: data });
  });
  await page.goto('/');
  await page.getByLabel('Usuario', { exact: true }).fill('O12345678');
  await page.getByLabel('Contraseña', { exact: true }).fill('fixture-password');
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click();
  await page.getByRole('heading', { name: 'Inicio', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Optimización', exact: true }).click();
  await expect(page.getByText('No hay pedidos pendientes.')).toBeVisible();
  await page.getByRole('button', { name: 'Explorar demostración' }).click();
}
async function capture(page, project, name) {
  await page.screenshot({ path: `${evidence}/${project}-${name}.png`, fullPage: true, animations: 'disabled' });
}
test('login, multiple selection, progressive First Fit, rotations, metrics and confirmation', async ({ page }, info) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await login(page); await capture(page, info.project.name, 'initial');
  await page.getByRole('checkbox', { name: /#21/ }).focus();
  await page.keyboard.press('Space');
  await expect(page.getByRole('checkbox', { name: /#21/ })).toBeChecked();
  await page.getByRole('checkbox', { name: /#22/ }).check();
  await expect(page.getByText('2 pedidos seleccionados')).toBeVisible();
  await page.getByRole('button', { name: 'Preparar optimización' }).click();
  await expect(page.getByText('Templado · 6 mm', { exact: true })).toBeVisible();
  await capture(page, info.project.name, 'groups');
  await page.getByRole('button', { name: 'Ejecutar First Fit', exact: true }).click();
  await expect(page.locator('[data-placement="21:101:0"]')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Resultado First Fit' })).toHaveCount(0);
  await capture(page, info.project.name, 'progress');
  await expect(page.getByRole('heading', { name: 'Resultado First Fit' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirmar solución', exact: true })).toBeVisible();
  await expect(page.getByText('4 / 4 piezas colocadas')).toBeVisible();
  await expect(page.locator('[data-placement="21:102:0"]')).toHaveAttribute('transform', /rotate\(90\)/);
  await expect(page.locator('[data-placement="22:104:0"]')).toHaveAttribute('transform', /rotate\(30\)/);
  const scale = await page.locator('.first-fit-sheet').evaluate(svg => { const m = svg.getScreenCTM(); return [m.a, m.d]; });
  expect(scale[0]).toBeCloseTo(scale[1], 5);
  await capture(page, info.project.name, 'result');
  await page.getByText('Inspeccionar geometría y raster de ejemplo · pieza #101', { exact: true }).click();
  await expect(page.getByRole('img', { name: 'Máscara raster de la pieza #101' })).toBeVisible();
  await capture(page, info.project.name, 'raster');
  await page.getByText('Inspeccionar geometría y raster de ejemplo · pieza #101', { exact: true }).click();
  await page.getByLabel('Plancha o retazo').selectOption('retazo:8');
  await expect(page.locator('[data-placement] circle')).toBeVisible();
  await page.getByRole('button', { name: 'Confirmar solución', exact: true }).click();
  const dialog = page.getByRole('alertdialog');
  await expect(dialog).toContainText('Esta operación puede modificar las existencias disponibles.');
  await expect(dialog.getByRole('button', { name: 'Cancelar' })).toBeFocused();
  await capture(page, info.project.name, 'confirm');
  await dialog.getByRole('button', { name: 'Confirmar solución', exact: true }).click();
  await expect(page.getByText(/No se guardó la solución/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
test('new order appears automatically without changing running snapshot', async ({ page }, info) => {
  await page.clock.install();
  await login(page);
  await page.getByLabel('Seleccionar todos').check();
  await page.getByRole('button', { name: 'Preparar optimización' }).click();
  await page.getByRole('button', { name: 'Ejecutar First Fit', exact: true }).click();
  await page.clock.runFor(7000);
  await expect(page.getByRole('checkbox', { name: /#24/ })).toBeVisible({ timeout: 12000 });
  await expect(page.getByRole('checkbox', { name: /#24/ })).not.toBeChecked();
  await expect(page.getByText('1 nuevo pedido disponible para la siguiente ejecución.')).toBeVisible();
  await expect(page.getByText(/Pedidos: #21, #22/)).toContainText('Piezas: 4');
  await expect(page.getByRole('button', { name: 'Actualizar pedidos' })).toHaveCount(0);
  await capture(page, info.project.name, 'live');
});

test('2D/3D result inspection preserves state with bounded mouse, touch and keyboard yaw', async ({ page }, info) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.clock.install();
  await login(page);
  await expect(page.getByRole('button', { name: 'Ver en 3D' })).toHaveCount(0);
  await page.getByRole('checkbox', { name: /#21/ }).check();
  await page.getByRole('checkbox', { name: /#22/ }).check();
  await page.getByRole('button', { name: 'Preparar optimización' }).click();
  await expect(page.getByRole('button', { name: 'Ver en 3D' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Ejecutar First Fit', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Ver en 3D' })).toHaveCount(0);
  await page.clock.runFor(6000);
  await page.getByRole('button', { name: 'Ver en 3D', exact: true }).click();
  const slider = page.getByRole('slider', { name: 'Giro horizontal de la vista 3D' });
  await expect(slider).toHaveAttribute('aria-valuenow', '-24');
  await expect(page.locator('[data-piece-3d]')).toHaveCount(3);
  await expect(page.getByRole('list', { name: 'Piezas en la vista 3D' })).toContainText('rotación aplicada: 30°');
  await slider.scrollIntoViewIfNeeded();
  const box = await slider.boundingBox();
  if (info.project.name === 'mobile') {
    const cdp = await page.context().newCDPSession(page);
    const y = box.y + box.height / 2;
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: box.x + box.width * 0.2, y }] });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: box.x + box.width * 0.8, y }] });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await expect(slider).not.toHaveAttribute('aria-valuenow', '-24');
    await cdp.detach();
  } else {
    await page.mouse.move(box.x + box.width * 0.1, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.95, box.y + box.height / 2, { steps: 8 });
    await page.mouse.up();
    await expect(slider).toHaveAttribute('aria-valuenow', '90');
  }
  await slider.focus(); await page.keyboard.press('Home'); await page.keyboard.press('ArrowLeft');
  await expect(slider).toHaveAttribute('aria-valuenow', '-90');
  await page.keyboard.press('End'); await page.keyboard.press('ArrowRight');
  await expect(slider).toHaveAttribute('aria-valuenow', '90');
  await page.getByRole('button', { name: 'Restablecer vista' }).click();
  await expect(slider).toHaveAttribute('aria-valuenow', '-24');
  expect(await slider.evaluate(el => getComputedStyle(el).animationName)).toBe('none');
  await page.getByRole('region', { name: 'Vista 3D del resultado' }).screenshot({ path: `${evidence}/${info.project.name}-3d.png`, animations: 'disabled' });
  await page.getByLabel('Plancha o retazo').selectOption('retazo:8');
  await expect(page.locator('[data-piece-3d="21:103:0"]')).toBeVisible();
  await page.getByRole('region', { name: 'Vista 3D del resultado' }).screenshot({ path: `${evidence}/${info.project.name}-3d-retazo.png`, animations: 'disabled' });
  await page.getByRole('button', { name: 'Ver en 2D', exact: true }).click();
  await expect(page.getByLabel('Plancha o retazo')).toHaveValue('retazo:8');
  await expect(page.getByRole('img', { name: 'Colocaciones en retazo #8' }).locator('circle')).toBeVisible();
  await expect(page.getByText('4 / 4 piezas colocadas')).toBeVisible();
  await expect(page.getByText('842 ms')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
