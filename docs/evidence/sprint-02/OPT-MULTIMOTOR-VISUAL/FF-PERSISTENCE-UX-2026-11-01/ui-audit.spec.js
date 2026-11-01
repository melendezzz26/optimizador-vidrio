// Observational audit. Runs only against the owned PostgreSQL E2E server.
import { test, expect } from '@playwright/test';
import { api, setup, login, capture, save } from './optimizationRealSupport.js';

test('auditoría transversal con API real, formularios, teclado y roles', async ({ page }, info) => {
  test.setTimeout(120000);
  const data = await setup(page, 'single');
  const observations = [], responses = [], errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {
    if (response.url().startsWith(api)) responses.push({ path: new URL(response.url()).pathname,
      method: response.request().method(), status: response.status() });
  });
  async function inspect(name) {
    await capture(page, info, name);
    const dom = await page.evaluate(() => {
      const visible = e => e.checkVisibility({ checkVisibilityCSS: true }) && e.getBoundingClientRect().width > 0;
      const label = e => e.getAttribute('aria-label') || [...(e.labels ?? [])].map(l => l.innerText).join(' ') || e.innerText || '';
      const controls = [...document.querySelectorAll('button,input,select,textarea,a[href],summary')].filter(visible).map(e => {
        const s = getComputedStyle(e), r = e.getBoundingClientRect();
        return { tag: e.tagName, type: e.type, text: label(e).trim().slice(0, 150), disabled: !!e.disabled,
          w: Math.round(r.width), h: Math.round(r.height), font: s.fontSize, radius: s.borderRadius,
          color: s.color, background: s.backgroundColor, labels: e.labels?.length ?? null,
          described: e.getAttribute('aria-describedby'), invalid: e.getAttribute('aria-invalid') };
      });
      const rgb = s => { const v = s.match(/[\d.]+/g)?.map(Number); return v?.length >= 3 && (v.length < 4 || v[3] === 1) ? v.slice(0, 3) : null; };
      const luminance = c => c.map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
        .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
      const contrasts = [];
      for (const e of [...document.querySelectorAll('p,small,label,span,button,th,td,h1,h2,h3,a')].filter(visible)) {
        if (e.children.length || !e.textContent.trim() || e.closest('[disabled]')) continue;
        const s = getComputedStyle(e), fg = rgb(s.color);
        let ancestor = e, bg;
        while (ancestor) {
          const style = getComputedStyle(ancestor);
          if (style.backgroundImage !== 'none' || Number(style.opacity) !== 1) break;
          bg = rgb(style.backgroundColor);
          if (bg) break;
          ancestor = ancestor.parentElement;
        }
        if (!fg || !bg) continue;
        const l = [luminance(fg), luminance(bg)].sort((a, b) => b - a), ratio = (l[0] + .05) / (l[1] + .05);
        const threshold = parseFloat(s.fontSize) >= 24 || parseFloat(s.fontSize) >= 18.666 && Number(s.fontWeight) >= 700 ? 3 : 4.5;
        if (ratio < threshold) contrasts.push({ text: e.textContent.trim().slice(0, 120), ratio: +ratio.toFixed(2),
          threshold, color: s.color, background: `rgb(${bg.join(',')})`, font: s.fontSize, weight: s.fontWeight });
      }
      return { width: innerWidth, scrollWidth: document.documentElement.scrollWidth, url: location.pathname,
        headings: [...document.querySelectorAll('h1,h2,h3')].filter(visible).map(e => ({ level: e.tagName, text: e.innerText })),
        focus: { tag: document.activeElement.tagName, text: label(document.activeElement).trim().slice(0, 120),
          outline: getComputedStyle(document.activeElement).outline, background: getComputedStyle(document.activeElement).backgroundColor },
        controls, contrastCandidates: contrasts,
        tableRegions: [...document.querySelectorAll('table')].filter(visible).map(e => ({ width: e.scrollWidth,
          container: e.parentElement.clientWidth, tabindex: e.parentElement.getAttribute('tabindex'), label: e.parentElement.getAttribute('aria-label') })) };
    });
    const viewport = page.viewportSize();
    await page.setViewportSize({ width: 320, height: 900 });
    const reflow320 = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth,
      overflowingRegions: [...document.querySelectorAll('[role="region"]')].filter(e => e.checkVisibility() && e.scrollWidth > e.clientWidth)
        .map(e => ({ name: e.getAttribute('aria-label'), scroll: e.scrollWidth, width: e.clientWidth })) }));
    await page.setViewportSize(viewport);
    observations.push({ name, ...dom, reflow320 });
  }
  async function navigate(name) { await page.getByRole('navigation', { name: 'Secciones', exact: true }).getByRole('button', { name, exact: true }).click(); }
  await page.goto('/');
  await inspect('01-login');
  await page.getByRole('button', { name: 'Ingresar', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Ingresa tu usuario.', { exact: true })).toBeVisible();
  await inspect('02-login-error');
  await login(page, { username: 'A70000003', password: 'Admin-test-2026!' }, { comparative: true });
  await expect(page.getByRole('button', { name: 'Actualizar datos', exact: true })).toBeEnabled();
  await inspect('03-dashboard-admin');
  await navigate('Administración');
  await expect(page.getByRole('heading', { name: 'Usuarios registrados', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Nuevo usuario', exact: true })).toBeEnabled();
  await inspect('04-usuarios');
  await page.getByRole('button', { name: 'Nuevo usuario', exact: true }).click();
  await inspect('05-usuario-formulario');
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await inspect('05b-usuario-retorno');
  const rolesTab = page.getByRole('tab', { name: 'Usuarios', exact: true });
  await rolesTab.focus(); await page.keyboard.press('End');
  await expect(page.getByRole('tab', { name: 'Roles y permisos', exact: true })).toBeFocused();
  await expect(page.getByLabel('Rol', { exact: true })).toBeEnabled();
  await page.getByLabel('Rol', { exact: true }).selectOption({ label: 'Operario' });
  await expect(page.getByRole('checkbox').first()).toBeVisible();
  await inspect('06-roles-permisos');
  await navigate('Gestión de inventario');
  await expect(page.getByRole('button', { name: 'Registrar plancha', exact: true })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Tabla de planchas', exact: true })).toBeVisible();
  await inspect('07-inventario-planchas');
  await page.getByRole('button', { name: 'Registrar plancha', exact: true }).click();
  await inspect('08-plancha-formulario');
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await page.getByRole('tab', { name: 'Planchas', exact: true }).focus(); await page.keyboard.press('End');
  await expect(page.getByRole('tab', { name: 'Retazos', exact: true })).toBeFocused();
  await inspect('09-inventario-retazos');
  await page.getByRole('button', { name: 'Registrar retazo', exact: true }).click();
  await inspect('10-retazo-formulario');
  const remnantCode = `AUDIT-${info.project.name}-${Date.now()}`;
  await page.getByLabel(/Código/).fill(remnantCode);
  await page.getByLabel(/Tipo de vidrio/).selectOption(String(data.materials[0].id_tipo_vidrio));
  await page.getByLabel(/Espesor/).selectOption(String(data.materials[0].espesor_mm));
  await page.getByLabel(/Tipo de forma/).selectOption('RECTANGULO');
  await page.getByLabel(/Ancho \(mm\)/).fill('10');
  await page.getByLabel(/Alto \(mm\)/).fill('10');
  const registered = page.waitForResponse(r => r.url() === api + '/api/inventory/retazos' && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Registrar retazo', exact: true }).click();
  expect((await registered).status()).toBe(201);
  await expect(page.getByRole('row', { name: new RegExp(remnantCode) })).toBeVisible();
  await inspect('10b-retazo-registrado');
  await navigate('Registro de pedidos');
  await expect(page.getByRole('button', { name: new RegExp(`Editar pedido ${data.orders[0]}$`) })).toBeVisible();
  await inspect('11-pedidos');
  await page.getByRole('button', { name: 'Nuevo pedido', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await inspect('12-pedido-formulario');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: new RegExp(`Editar pedido ${data.orders[0]}$`) }).click();
  await expect(page.getByRole('dialog').getByLabel('Cantidad', { exact: true })).toHaveValue('1');
  await inspect('13-pedido-editar');
  await page.locator('.orders-group-toggle').first().click();
  await page.getByRole('dialog').getByLabel('Cantidad', { exact: true }).fill('2');
  // Characterize a backlog defect: Escape currently discards unsaved input.
  await page.keyboard.press('Escape');
  await expect(page.getByRole('alertdialog')).toHaveCount(0);
  await page.getByRole('button', { name: new RegExp(`Editar pedido ${data.orders[0]}$`) }).click();
  await expect(page.getByRole('dialog').getByLabel('Cantidad', { exact: true })).toHaveValue('1');
  await inspect('13b-pedido-reabrir-despues-escape');
  await page.keyboard.press('Escape');
  await navigate('Optimización');
  await expect(page.getByRole('checkbox', { name: new RegExp(`Pedido #${data.orders[0]}\\b`) })).toBeVisible();
  await inspect('14-optimizacion-pendientes');
  await page.getByRole('checkbox', { name: new RegExp(`Pedido #${data.orders[0]}\\b`) }).check();
  await page.getByRole('button', { name: 'Comparar con los tres motores', exact: true }).click();
  await expect(page.getByText('Comparación finalizada', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: /First Fit/ }).focus();
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowLeft');
  await expect(page.getByRole('tab', { name: /First Fit/ })).toBeFocused();
  await inspect('14b-optimizacion-resultado');
  await page.getByRole('tab', { name: 'Comparación', exact: true }).click();
  await inspect('14c-optimizacion-tabla');
  await page.getByRole('button', { name: 'Liberar pedidos sin confirmar', exact: true }).click();
  await expect(page.getByRole('tab')).toHaveCount(0);
  // 320 CSS px is the reflow reference, separate from 390 px mobile screenshots.
  const viewport = page.viewportSize();
  await page.setViewportSize({ width: 320, height: 900 });
  await inspect('15-reflow-320');
  await page.setViewportSize(viewport);
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
  await expect(page.getByLabel('Usuario', { exact: true })).toBeVisible();
  for (const [name, username, password] of [
    ['operario', 'O70000001', 'Orders-test-2026!'], ['almacenero', 'A70000002', 'Inventory-test-2026!'],
    ['sin-funciones', 'O70000004', 'Dashboard-test-2026!']]) {
    await login(page, { username, password }, { comparative: true });
    if (name !== 'sin-funciones') await expect(page.getByRole('button', { name: 'Actualizar datos', exact: true })).toBeEnabled();
    else await expect(page.getByText('Sin funciones habilitadas', { exact: true })).toBeVisible();
    await inspect(`16-dashboard-${name}`);
    await expect(page.getByRole('navigation', { name: 'Secciones', exact: true }).getByRole('button', { name: 'Administración', exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
  }
  save(info, 'ui-audit-observations.json', { observations, responses, errors });
  expect(errors).toEqual([]);
});
