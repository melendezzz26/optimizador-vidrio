import { Buffer } from 'node:buffer'
import { test, expect } from '@playwright/test'

const api = 'http://127.0.0.1:8017'
const user = { username: 'A70000003', password: 'Admin-test-2026!' }
async function login(page) {
  await page.goto('/')
  await page.getByLabel('Usuario', { exact: true }).fill(user.username)
  await page.getByLabel('Contrase\u00f1a', { exact: true }).fill(user.password)
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Cerrar sesi\u00f3n', exact: true })).toBeVisible()
}
async function go(page, name) {
  await page.getByRole('button', { name, exact: true }).first().click()
}
async function noPageOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy()
}

test('CF-01 login real y navegacion', async ({ page, browser }) => {
  test.info().annotations.push({ type: 'browser-version', description: browser.version() })
  await login(page)
  await expect(page.getByRole('heading', { name: 'Resumen operativo' })).toBeVisible()
  await noPageOverflow(page)
  if (['chrome-desktop', 'chrome-mobile'].includes(test.info().project.name)) {
    await page.screenshot({ path: `../docs/evidence/sprint-02/TA-QA-008/${test.info().project.name}.png`, animations: 'disabled' })
  }
})

test('CF-02 pedidos, formulario e importacion', async ({ page }) => {
  await login(page)
  await go(page, 'Registro de pedidos')
  await expect(page.getByRole('heading', { name: 'Pedidos registrados' })).toBeVisible()
  await page.getByRole('button', { name: 'Nuevo pedido' }).click()
  const dialog = page.getByRole('dialog', { name: 'Crear pedido' })
  await expect(dialog.getByLabel('Nombre del cliente')).toBeVisible()
  await dialog.getByLabel('Nombre del cliente').fill('Vidrios Norte')
  await dialog.getByRole('button', { name: 'Buscar', exact: true }).click()
  await dialog.getByRole('button', { name: 'Seleccionar Vidrios Norte' }).click()
  await expect(dialog.getByRole('button', { name: 'Importar CSV/XLSX' })).toBeVisible()
  await dialog.getByLabel('Tipo de vidrio', { exact: true }).selectOption('7')
  await dialog.getByLabel('Espesor del vidrio (mm)', { exact: true }).selectOption('6')
  await dialog.getByLabel('Ancho (mm)').fill('100')
  await dialog.getByLabel('Alto (mm)').fill('200')
  const saved = page.waitForResponse(r => new URL(r.url()).pathname === '/api/orders' && r.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Guardar pedido' }).click()
  expect((await saved).status()).toBe(201)
  await noPageOverflow(page)
})

test('CF-03 inventario y formulario de plancha', async ({ page }) => {
  await login(page)
  await go(page, 'Gesti\u00f3n de inventario')
  await expect(page.getByRole('tab', { name: 'Planchas' })).toBeVisible()
  await page.getByRole('tab', { name: 'Retazos' }).click()
  await expect(page.getByRole('tab', { name: 'Retazos' })).toHaveAttribute('aria-selected', 'true')
  await page.getByRole('tab', { name: 'Planchas' }).click()
  await page.getByRole('button', { name: 'Registrar plancha', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Registrar plancha comercial' })).toBeVisible()
  await page.getByLabel('Tipo de vidrio *', { exact: true }).selectOption('7')
  await page.getByLabel('Espesor (mm) *', { exact: true }).selectOption('6')
  await page.getByLabel('Ancho (mm)').fill('250')
  await page.getByLabel('Alto (mm)').fill('350')
  await page.getByLabel('Cantidad').fill('1')
  const saved = page.waitForResponse(r => new URL(r.url()).pathname === '/api/inventory/planchas' && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Registrar plancha', exact: true }).click()
  expect((await saved).status()).toBe(201)
  await noPageOverflow(page)
})

test('CF-06 rutas y controles principales', async ({ page }) => {
  await login(page)
  for (const [button, heading] of [['Registro de pedidos', 'Gesti\u00f3n de pedidos'],
    ['Gesti\u00f3n de inventario', 'Gesti\u00f3n de Inventario'], ['Optimizaci\u00f3n', 'Optimizaci\u00f3n de corte'], ['Inicio', 'Resumen operativo']]) {
    await go(page, button)
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
    await noPageOverflow(page)
  }
})

test('CF-04 y CF-05 comparacion real', async ({ page, request }) => {
  const auth = await request.post(`${api}/api/auth/login`, { data: user })
  expect(auth.status()).toBe(200)
  const token = (await auth.json()).access_token
  const sheet = await request.post(`${api}/api/inventory/planchas`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { id_tipo_vidrio: 7, espesor_mm: 6, ancho_mm: 250, alto_mm: 350, cantidad: 1 },
  })
  expect(sheet.status()).toBe(201)
  const order = await request.post(`${api}/api/orders`, { headers: { Authorization: `Bearer ${token}` }, data: {
    id_cliente: 41, piezas: [{ id_tipo_vidrio: 7, espesor_mm: 6, tipo_forma: 'RECTANGULO', cantidad: 1, width_mm: 50, height_mm: 50 }],
  } })
  expect(order.status()).toBe(201)
  const id = (await order.json()).id_pedido
  await login(page)
  await go(page, 'Optimizaci\u00f3n')
  await page.getByRole('checkbox', { name: new RegExp(`Pedido #${id}\\b`) }).check()
  await page.getByLabel('M\u00e9todos').selectOption('comparison-v2')
  const accepted = page.waitForResponse(r => new URL(r.url()).pathname === '/api/optimization/comparisons-v2' && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Comparar con los seis motores', exact: true }).click()
  const acceptedResponse = await accepted
  expect(acceptedResponse.status()).toBe(201)
  const comparison = await acceptedResponse.json()
  await expect(page.getByText('Comparaci\u00f3n finalizada', { exact: true })).toBeVisible({ timeout: 90000 })
  const outcome = await request.get(`${api}/api/optimization/comparisons-v2/${comparison.comparison_id}`, { headers: { Authorization: `Bearer ${token}` } })
  expect(outcome.status()).toBe(200)
  const executions = (await outcome.json()).executions
  expect(executions).toHaveLength(6)
  expect(executions.every(e => e.complete && e.result_available)).toBeTruthy()
  await page.getByRole('tab', { name: 'Comparaci\u00f3n', exact: true }).click()
  await expect(page.getByRole('tablist', { name: 'Motores y comparaci\u00f3n' })).toBeVisible()
  const choice = page.getByRole('radio', { name: 'Elegir First Fit' })
  await choice.check()
  await expect(choice).toBeChecked()
  await expect(page.getByRole('button', { name: 'Confirmar distribuci\u00f3n elegida' })).toBeEnabled()
  if (['chrome-desktop', 'chrome-mobile'].includes(test.info().project.name)) {
    await page.screenshot({ path: `../docs/evidence/sprint-02/TA-QA-008/${test.info().project.name}-comparacion.png`, animations: 'disabled' })
  }
  await noPageOverflow(page)
})

test('CF-02 importacion real de CSV', async ({ page }) => {
  await login(page)
  await go(page, 'Registro de pedidos')
  await page.getByRole('button', { name: 'Nuevo pedido' }).click()
  const dialog = page.getByRole('dialog', { name: 'Crear pedido' })
  await dialog.getByLabel('Nombre del cliente').fill('Vidrios Norte')
  await dialog.getByRole('button', { name: 'Buscar', exact: true }).click()
  await dialog.getByRole('button', { name: 'Seleccionar Vidrios Norte' }).click()
  await dialog.getByRole('button', { name: 'Importar CSV/XLSX' }).click()
  const panel = page.getByRole('region', { name: 'Importar piezas desde archivo' })
  await panel.getByLabel('Archivo CSV o XLSX').setInputFiles({ name: 'piezas.csv', mimeType: 'text/csv', buffer: Buffer.from('tipo,cantidad,medidas\nR,1,100,200') })
  await panel.getByLabel('Tipo de vidrio para estas piezas').selectOption('7')
  await panel.getByLabel('Espesor (mm)').selectOption('6')
  await panel.getByRole('button', { name: 'Agregar al pedido' }).click()
  await expect(panel).toHaveCount(0)
  const saved = page.waitForResponse(r => new URL(r.url()).pathname === '/api/orders' && r.request().method() === 'POST')
  await dialog.getByRole('button', { name: 'Guardar pedido' }).click()
  expect((await saved).status()).toBe(201)
  await noPageOverflow(page)
})

test('CF-03 edicion y formulario de retazo', async ({ page }) => {
  await login(page)
  await go(page, 'Gesti\u00f3n de inventario')
  await page.getByRole('button', { name: 'Editar', exact: true }).first().click()
  await expect(page.getByRole('heading', { name: 'Editar plancha' })).toBeVisible()
  const width = page.getByLabel('Ancho (mm)')
  await width.fill(String(Number(await width.inputValue()) + 1))
  const edited = page.waitForResponse(r => /\/api\/inventory\/planchas\/\d+$/.test(new URL(r.url()).pathname) && r.request().method() === 'PATCH')
  await page.getByRole('button', { name: 'Guardar cambios', exact: true }).click()
  expect((await edited).status()).toBe(200)
  await page.getByRole('tab', { name: 'Retazos' }).click()
  await page.getByRole('button', { name: 'Registrar retazo', exact: true }).click()
  await expect(page.getByLabel('Tipo de vidrio *', { exact: true })).toBeVisible()
  await page.getByLabel('C\u00f3digo *', { exact: true }).fill(`QA008-${Date.now()}`)
  await page.getByLabel('Tipo de vidrio *', { exact: true }).selectOption('7')
  await page.getByLabel('Espesor (mm) *', { exact: true }).selectOption('6')
  await page.getByLabel('Tipo de forma *', { exact: true }).selectOption('RECTANGULO')
  await page.getByLabel('Ancho (mm) *', { exact: true }).fill('250')
  await page.getByLabel('Alto (mm) *', { exact: true }).fill('350')
  const saved = page.waitForResponse(r => new URL(r.url()).pathname === '/api/inventory/retazos' && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Registrar retazo', exact: true }).click()
  expect((await saved).status()).toBe(201)
  await noPageOverflow(page)
})

test('CF-07 reflujo y controles criticos', async ({ page }) => {
  async function inspect(control) {
    await noPageOverflow(page)
    await expect(control).toBeVisible()
    await control.scrollIntoViewIfNeeded()
    await expect(control).toBeInViewport()
    await control.click({ trial: true })
  }
  await page.goto('/')
  await inspect(page.getByRole('button', { name: 'Ingresar', exact: true }))
  await login(page)
  await inspect(page.getByRole('button', { name: 'Actualizar datos', exact: true }))
  await go(page, 'Registro de pedidos')
  await inspect(page.getByRole('button', { name: 'Nuevo pedido', exact: true }))
  await page.getByRole('button', { name: 'Nuevo pedido', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Crear pedido' })
  await inspect(dialog.getByRole('button', { name: 'Importar CSV/XLSX' }))
  if (['chrome-desktop', 'chrome-mobile'].includes(test.info().project.name)) {
    await page.screenshot({ path: `../docs/evidence/sprint-02/TA-QA-008/${test.info().project.name}-pedido.png`, animations: 'disabled' })
  }
  await dialog.getByRole('button', { name: 'Cerrar formulario de pedido', exact: true }).click()
  await expect(dialog).toHaveCount(0)
  await go(page, 'Gesti\u00f3n de inventario')
  await inspect(page.getByRole('button', { name: 'Registrar plancha', exact: true }))
  await page.getByRole('button', { name: 'Registrar plancha', exact: true }).click()
  await inspect(page.getByLabel('Tipo de vidrio *', { exact: true }))
  await go(page, 'Optimizaci\u00f3n')
  await inspect(page.getByLabel('M\u00e9todos'))
  if (['chrome-desktop', 'chrome-mobile'].includes(test.info().project.name)) {
    await page.screenshot({ path: `../docs/evidence/sprint-02/TA-QA-008/${test.info().project.name}-optimizacion.png`, animations: 'disabled' })
  }
})

test('CF-01 mensajes obligatorios de login', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click()
  await expect(page.getByText('Ingresa tu usuario.', { exact: true })).toBeVisible()
  await expect(page.getByText('Ingresa tu contrase\u00f1a.', { exact: true })).toBeVisible()
  await noPageOverflow(page)
})
