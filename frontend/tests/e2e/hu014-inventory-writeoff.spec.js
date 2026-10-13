import { test, expect } from '@playwright/test'

const apiOrigin = 'http://127.0.0.1:8017'
const planchaId = 701

async function signInAndOpenInventory(page, username, password) {
  await page.goto('/')
  await page.getByLabel('Usuario', { exact: true }).fill(username)
  await page.getByLabel('Contraseña', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click()
  await page.getByRole('button', { name: 'Gestión de inventario', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Gestión de Inventario' })).toBeVisible()
}

test('HU-014: Almacenero registra una baja y consulta el movimiento persistido', async ({ page }, testInfo) => {
  // Esta baja agota el saldo. Ejecutarla una vez evita que el segundo
  // viewport reutilice el mismo fixture ya dado de baja.
  test.skip(testInfo.project.name !== 'chromium-desktop', 'La mutación agota un recurso compartido entre viewports.')

  await signInAndOpenInventory(page, 'A70000002', 'Inventory-test-2026!')
  await expect(page.getByRole('row', { name: /Material de prueba/ })).toContainText('Activo')

  const historyButton = page.getByRole('button', {
    name: `Ver historial de plancha #${planchaId}`,
    exact: true,
  })
  await historyButton.click()
  const emptyHistory = page.getByRole('dialog', {
    name: `Historial de movimientos · Plancha #${planchaId}`,
  })
  await expect(emptyHistory).toContainText('No hay movimientos registrados para este material.')
  await emptyHistory.getByRole('button', { name: 'Cerrar diálogo' }).click()

  await page.getByRole('button', {
    name: `Dar de baja plancha #${planchaId}`,
    exact: true,
  }).click()
  const writeoffDialog = page.getByRole('dialog', { name: 'Dar de baja plancha' })
  await expect(writeoffDialog).toBeVisible()
  await expect(writeoffDialog.getByLabel('Tipo de baja')).toBeFocused()
  await writeoffDialog.getByLabel('Cantidad a dar de baja').fill('2')
  await writeoffDialog.getByLabel('Tipo de baja').selectOption('BAJA_ROTURA')
  await writeoffDialog.getByLabel('Motivo').fill('Rotura durante el almacenamiento')
  await writeoffDialog.getByLabel('Observación (opcional)').fill('Prueba E2E sintética')

  await writeoffDialog.getByRole('button', { name: 'Revisar baja' }).click()
  const reviewDialog = page.getByRole('dialog', { name: 'Confirmar baja manual' })
  await expect(reviewDialog).toContainText('Material de prueba')
  await expect(reviewDialog).toContainText('Rotura')
  await expect(reviewDialog).toContainText('Rotura durante el almacenamiento')
  await expect(reviewDialog).toContainText('el material quedará inactivo')

  const posts = []
  page.on('request', (request) => {
    if (request.url() === `${apiOrigin}/api/inventory/planchas/${planchaId}/baja` && request.method() === 'POST') {
      posts.push(request)
    }
  })
  const writeoffResponse = page.waitForResponse((response) => (
    response.url() === `${apiOrigin}/api/inventory/planchas/${planchaId}/baja`
      && response.request().method() === 'POST'
  ))
  await reviewDialog.getByRole('button', { name: 'Confirmar baja' }).click()
  const response = await writeoffResponse
  expect(response.status()).toBe(201)
  expect(posts).toHaveLength(1)
  expect(posts[0].postDataJSON()).toEqual({
    cantidad_afectada: 2,
    tipo_evento: 'BAJA_ROTURA',
    motivo: 'Rotura durante el almacenamiento',
    observacion: 'Prueba E2E sintética',
  })
  await expect(page.getByText(/Baja registrada correctamente\. Movimiento #\d+\./)).toBeVisible()

  const planchaRow = page.getByRole('row', { name: /Material de prueba/ })
  await expect(planchaRow).toBeVisible()
  await expect(planchaRow).toContainText('Inactivo')
  await expect(planchaRow.getByRole('button', {
    name: `Ver historial de plancha #${planchaId}`,
  })).toBeVisible()

  await planchaRow.getByRole('button', {
    name: `Ver historial de plancha #${planchaId}`,
  }).click()
  const movementHistory = page.getByRole('dialog', {
    name: `Historial de movimientos · Plancha #${planchaId}`,
  })
  await expect(movementHistory.getByRole('heading', { name: 'Baja por rotura' })).toBeVisible()
  await expect(movementHistory).toContainText('Rotura durante el almacenamiento')
  await expect(movementHistory).toContainText('Prueba E2E sintética')
  await expect(movementHistory).toContainText('Usuario #2')
  const movementDate = movementHistory.locator('time')
  await expect(movementDate).toBeVisible()
  await expect(movementDate).toHaveAttribute('datetime', /^\d{4}-\d{2}-\d{2}T/)
})

test('HU-014: Operario consulta inventario, pero no ve acciones de gestión', async ({ page }) => {
  await signInAndOpenInventory(page, 'O70000001', 'Orders-test-2026!')
  await expect(page.getByRole('button', {
    name: `Ver historial de plancha #${planchaId}`,
  })).toBeVisible()
  await expect(page.getByRole('button', {
    name: `Dar de baja plancha #${planchaId}`,
  })).toHaveCount(0)
})
