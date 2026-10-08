import { test, expect } from '@playwright/test'

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
  await page.getByLabel('Tipo de vidrio').selectOption('7')
  await page.getByLabel('Espesor', { exact: true }).selectOption('5.5')
})

async function drawValid(page) {
  const canvas = page.getByRole('img', { name: /Lienzo del dibujo original/ })
  await canvas.scrollIntoViewIfNeeded()
  for (const point of [[100, 100], [400, 100], [400, 300], [100, 300]]) {
    const position = await canvas.evaluate((svg, [x, y]) => {
      const screen = new DOMPoint(x, y).matrixTransform(svg.getScreenCTM())
      return { x: screen.x, y: screen.y }
    }, point)
    await page.mouse.click(position.x, position.y)
  }
  await page.getByRole('button', { name: 'Cerrar polígono' }).click()
  await expect(page.getByRole('button', { name: 'Agregar pieza al pedido' })).toBeDisabled()
  for (const [index, value] of [300, 200, 300, 200].entries()) {
    await page.getByRole('spinbutton', { name: `Longitud del segmento S${index + 1} en milímetros` }).fill(String(value))
  }
  await expect(page.getByText('Geometría convexa validada.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Agregar pieza al pedido' })).toBeEnabled()
}

test('T04: login JWT real, múltiples piezas locales, POST único y 201', async ({ page }, testInfo) => {
  const posts = []
  page.on('request', (request) => { if (request.url() === `${apiOrigin}/api/orders`) posts.push(request) })
  await drawValid(page)
  await page.screenshot({ path: testInfo.outputPath('poligono-valid.png'), fullPage: true })
  await page.getByRole('button', { name: 'Agregar pieza al pedido' }).click()
  await expect(page.getByText('Pieza 1', { exact: true })).toBeVisible()
  await expect(page.getByText('0 vértices')).toBeVisible()
  await drawValid(page)
  await page.getByRole('button', { name: 'Agregar pieza al pedido' }).click()
  expect(posts).toHaveLength(0)
  await page.screenshot({ path: testInfo.outputPath('piezas-locales.png'), fullPage: true })
  const saved = page.waitForResponse((response) => response.url() === `${apiOrigin}/api/orders`)
  await page.getByRole('button', { name: 'Guardar pedido' }).dblclick()
  const response = await saved
  expect(response.status()).toBe(201)
  const { id_pedido } = await response.json()
  await expect(page.getByText(`Pedido guardado correctamente. ID del pedido: ${id_pedido}.`)).toBeVisible()
  expect(posts).toHaveLength(1)
  expect(posts[0].postDataJSON().piezas).toHaveLength(2)
  await expect(page.getByRole('button', { name: 'Guardar pedido' })).toBeDisabled()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('pedido-guardado.png'), fullPage: true })
})

test('T04: error de red conserva pieza y reintento llega al backend real', async ({ page }) => {
  await drawValid(page)
  await page.getByRole('button', { name: 'Agregar pieza al pedido' }).click()
  await page.route(`${apiOrigin}/api/orders`, (route) => route.abort(), { times: 1 })
  await page.getByRole('button', { name: 'Guardar pedido' }).click()
  await expect(page.getByRole('alert')).toContainText('Las piezas se conservan')
  await expect(page.getByText('Pieza 1', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Guardar pedido' }).click()
  await expect(page.getByText(/Pedido guardado correctamente. ID del pedido:/)).toBeVisible()
})
