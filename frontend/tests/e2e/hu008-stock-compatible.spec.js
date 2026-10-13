import { expect, test } from '@playwright/test'

const apiOrigin = 'http://127.0.0.1:8017'

async function openOrderForm(page, baseURL) {
  await page.route('**/*', (route) => [baseURL, apiOrigin].includes(new URL(route.request().url()).origin)
    ? route.continue() : route.abort())
  await page.goto('/')
  await page.getByLabel('Usuario', { exact: true }).fill('O70000001')
  await page.getByLabel('Contraseña', { exact: true }).fill('Orders-test-2026!')
  const loginResponse = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/auth/login`)
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click()
  const login = await loginResponse
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` }
  await page.getByRole('button', { name: 'Nuevo pedido', exact: true }).click()
  await expect(page.getByRole('dialog', { name: 'Crear pedido', exact: true })).toBeVisible()
  return headers
}

async function selectExistingClient(page) {
  await page.getByLabel('Nombre del cliente').fill('Vidrios Norte')
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await page.getByRole('button', { name: 'Seleccionar Vidrios Norte' }).click()
}

async function addRectangle(page, width, height) {
  await page.getByRole('button', { name: 'Agregar pieza', exact: true }).click()
  const piece = page.locator('.orders-piece').last()
  await piece.getByLabel('Material', { exact: true }).selectOption('7')
  await piece.getByLabel('Espesor', { exact: true }).selectOption('5.5')
  await piece.getByLabel('Ancho (mm)', { exact: true }).fill(String(width))
  await piece.getByLabel('Alto (mm)', { exact: true }).fill(String(height))
  return piece
}

test('HU-008 registra una pieza con candidato individual y deja el stock igual', async ({ page, baseURL }) => {
  const headers = await openOrderForm(page, baseURL)
  await selectExistingClient(page)
  await addRectangle(page, 300, 200)
  const stockBeforeResponse = await page.request.get(`${apiOrigin}/api/inventory/planchas`, { headers })
  expect(stockBeforeResponse.status()).toBe(200)
  const stockBefore = (await stockBeforeResponse.json()).map(({ id_plancha, cantidad, estado }) => ({ id_plancha, cantidad, estado }))

  const saved = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/orders` && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Guardar pedido' }).click()
  const response = await saved
  expect(response.status()).toBe(201)
  const order = await response.json()
  expect(order.id_cliente).toBe(41)
  await expect(page.getByText(`Pedido registrado correctamente. ID del pedido: ${order.id_pedido}.`)).toBeVisible()

  const stockAfterResponse = await page.request.get(`${apiOrigin}/api/inventory/planchas`, { headers })
  expect(stockAfterResponse.status()).toBe(200)
  const stockAfter = (await stockAfterResponse.json()).map(({ id_plancha, cantidad, estado }) => ({ id_plancha, cantidad, estado }))
  expect(stockAfter).toEqual(stockBefore)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('HU-008 identifica una pieza sin candidato y no registra el pedido ni altera el stock', async ({ page, baseURL }) => {
  const headers = await openOrderForm(page, baseURL)
  const clientName = `HU-008 sin candidato ${crypto.randomUUID()}`
  await page.getByRole('button', { name: 'Registrar nuevo cliente' }).click()
  await page.getByLabel('Nombre o razón social', { exact: true }).fill(clientName)
  const createdClient = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/clients` && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Registrar y seleccionar' }).click()
  expect((await createdClient).status()).toBe(201)

  const stockBeforeResponse = await page.request.get(`${apiOrigin}/api/inventory/planchas`, { headers })
  expect(stockBeforeResponse.status()).toBe(200)
  const stockBefore = (await stockBeforeResponse.json()).map(({ id_plancha, cantidad, estado }) => ({ id_plancha, cantidad, estado }))
  await addRectangle(page, 1001, 501)
  const rejected = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/orders` && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Guardar pedido' }).click()
  const response = await rejected
  expect(response.status()).toBe(422)
  expect((await response.json()).detail).toMatchObject({
    code: 'NO_COMPATIBLE_STOCK',
    pieces: [{ index: 1 }],
  })
  await expect(page.getByRole('alert')).toContainText('Pieza 1')
  await expect(page.locator('.orders-piece').first()).toContainText('No hay plancha ni retazo disponible')
  await expect(page.getByLabel('Cliente seleccionado')).toContainText(clientName)
  await expect(page.getByText('Pieza 1', { exact: true })).toBeVisible()

  const ordersResponse = await page.request.get(`${apiOrigin}/api/orders?cliente=${encodeURIComponent(clientName)}`, { headers })
  expect(ordersResponse.status()).toBe(200)
  expect((await ordersResponse.json()).items).toEqual([])
  const stockAfterResponse = await page.request.get(`${apiOrigin}/api/inventory/planchas`, { headers })
  expect(stockAfterResponse.status()).toBe(200)
  const stockAfter = (await stockAfterResponse.json()).map(({ id_plancha, cantidad, estado }) => ({ id_plancha, cantidad, estado }))
  expect(stockAfter).toEqual(stockBefore)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
