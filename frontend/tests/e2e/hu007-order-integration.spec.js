import { test, expect } from '@playwright/test'
import { edgeLengths, interiorAngles } from '../../src/features/orders/polygonMeasurements.js'

const apiOrigin = 'http://127.0.0.1:8017'

test.beforeEach(async ({ page, baseURL }) => {
  await page.route('**/*', async (route) => {
    const origin = new URL(route.request().url()).origin
    if (![baseURL, apiOrigin].includes(origin)) await route.abort()
    else await route.continue()
  })
  await page.goto('/')
  await page.getByLabel('Usuario', { exact: true }).fill('O70000001')
  await page.getByLabel('Contraseña', { exact: true }).fill('Orders-test-2026!')
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click()
  await page.getByRole('button', { name: 'Nuevo pedido', exact: true }).click()
  await page.getByLabel('Nombre del cliente').fill('Vidrios Norte')
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await page.getByRole('button', { name: 'Seleccionar Vidrios Norte' }).click()
})

async function drawValid(page, points = [[100, 100], [400, 100], [400, 300], [100, 300]], sides = [300, 200, 300, 200]) {
  await page.getByRole('button', { name: 'Agregar pieza', exact: true }).click()
  const row = page.locator('.orders-piece').last()
  await row.getByLabel('Material', { exact: true }).selectOption('7')
  await row.getByLabel('Espesor', { exact: true }).selectOption('5.5')
  await row.getByLabel('Forma', { exact: true }).selectOption('POLIGONO_CONVEXO')
  const canvas = page.getByRole('img', { name: /Lienzo del dibujo original/ })
  await canvas.scrollIntoViewIfNeeded()
  for (const point of points) {
    const position = await canvas.evaluate((svg, [x, y]) => {
      const screen = new DOMPoint(x, y).matrixTransform(svg.getScreenCTM())
      return { x: screen.x, y: screen.y }
    }, point)
    await page.mouse.click(position.x, position.y)
  }
  await page.getByRole('button', { name: 'Cerrar polígono' }).click()
  await expect(page.getByRole('button', { name: 'Agregar pieza al pedido' })).toBeDisabled()
  for (const [index, value] of sides.entries()) {
    await page.getByRole('spinbutton', { name: `Longitud del segmento S${index + 1} en milímetros` }).fill(String(value))
  }
  await expect(page.getByText('Geometría convexa validada.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Agregar pieza al pedido' })).toBeEnabled()
}

test('lados independientes: POST y lectura real conservan triángulo, cuadrilátero angular y pentágono', async ({ page }) => {
  const cases = [
    { sides: [50, 70, 65], points: [[100, 100], [450, 100], [300, 400]] },
    { sides: [120, 73, 91, 108], points: [[100, 100], [450, 100], [450, 400], [100, 400]], angle: 110 },
    { sides: [80, 115, 63, 92, 71], points: [[200, 50], [500, 50], [600, 250], [350, 450], [100, 250]] },
  ]
  for (const item of cases) {
    await drawValid(page, item.points, item.sides)
    if (item.angle) {
      await page.getByRole('combobox', { name: 'Configuración geométrica' }).selectOption('angle')
      await page.getByRole('spinbutton', { name: /Ángulo interior fijado/ }).fill(String(item.angle))
    }
    await page.getByRole('button', { name: 'Agregar pieza al pedido' }).click()
  }
  const saved = page.waitForResponse(response => response.url() === `${apiOrigin}/api/orders` && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Guardar pedido' }).click()
  const response = await saved
  expect(response.status()).toBe(201)
  const { id_pedido } = await response.json()
  const read = await page.request.get(`${apiOrigin}/api/orders/${id_pedido}`, { headers: { Authorization: response.request().headers().authorization } })
  expect(read.status()).toBe(200)
  const { piezas } = await read.json()
  expect(piezas).toHaveLength(3)
  for (const item of cases) {
    const piece = piezas.find(piece => piece.geometria.vertices_mm.length === item.sides.length)
    expect(piece).toBeTruthy()
    edgeLengths(piece.geometria.vertices_mm).forEach((side, i) => expect(side).toBeCloseTo(item.sides[i], 6))
    if (item.angle) expect(interiorAngles(piece.geometria.vertices_mm)[1]).toBeCloseTo(item.angle, 6)
  }
})

test('T04: login JWT real, múltiples piezas locales, POST único y 201', async ({ page }) => {
  const posts = []
  page.on('request', (request) => { if (request.url() === `${apiOrigin}/api/orders` && request.method() === 'POST') posts.push(request) })
  await drawValid(page)
  await page.getByRole('button', { name: 'Agregar pieza al pedido' }).click()
  await expect(page.getByText('Pieza 1', { exact: true })).toBeVisible()
  await expect(page.getByRole('img', { name: /Lienzo del dibujo original/ })).toHaveCount(0)
  await drawValid(page)
  await page.getByRole('button', { name: 'Agregar pieza al pedido' }).click()
  expect(posts).toHaveLength(0)
  const saved = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/orders` && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Guardar pedido' }).click()
  const response = await saved
  expect(response.status()).toBe(201)
  const { id_pedido } = await response.json()
  await expect(page.getByText(`Pedido registrado correctamente. ID del pedido: ${id_pedido}.`)).toBeVisible()
  expect(posts).toHaveLength(1)
  expect(posts[0].postDataJSON().piezas).toHaveLength(2)
  expect(posts[0].postDataJSON().id_cliente).toBe(41)
  const read = await page.request.get(`${apiOrigin}/api/orders/${id_pedido}`, { headers: { Authorization: posts[0].headers().authorization } })
  expect(read.status()).toBe(200)
  const order = await read.json()
  expect(order.id_cliente).toBe(41)
  expect(order.id_usuario_registro).not.toBe(41)
  expect(order.piezas).toHaveLength(2)
  await expect(page.getByRole('dialog', { name: 'Crear pedido' })).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('T04: error de red conserva pieza y reintento llega al backend real', async ({ page }) => {
  await drawValid(page)
  await page.getByRole('button', { name: 'Agregar pieza al pedido' }).click()
  await page.route(`${apiOrigin}/api/orders`, (route) => route.abort(), { times: 1 })
  await page.getByRole('button', { name: 'Guardar pedido' }).click()
  await expect(page.getByRole('alert')).toContainText('Las piezas y el cliente se conservan')
  await expect(page.getByText('Pieza 1', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Guardar pedido' }).click()
  await expect(page.getByText(/Pedido registrado correctamente. ID del pedido:/)).toBeVisible()
})
