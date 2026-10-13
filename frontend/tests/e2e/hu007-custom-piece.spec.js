import { test as base, expect } from '@playwright/test'

const pentagon = [[200, 50], [500, 50], [600, 250], [350, 450], [100, 250]]
const lengths = [850, 420, 600, 510, 730]
const field = (page, id) => page.getByRole('spinbutton', { name: `Longitud del segmento S${id} en milímetros` })
const addButton = (page) => page.getByRole('button', { name: 'Agregar pieza al pedido' })

const test = base.extend({ page: async ({ page, baseURL }, runWithPage) => {
  // Fail on unexpected external traffic before it can reach a shared service.
  // This is a network guard, not a simulated API or integration test.
  const unexpected = []
  await page.route('**/*', async (route) => {
    const request = route.request()
    if (new URL(request.url()).origin !== baseURL || request.method() !== 'GET' ||
        ['xhr', 'fetch'].includes(request.resourceType())) {
      unexpected.push(`${request.method()} ${request.url()}`)
      await route.abort()
    } else await route.continue()
  })
  page.on('pageerror', (error) => unexpected.push(error.message))
  await runWithPage(page)
  expect(unexpected, 'No external/API requests or uncaught browser errors').toEqual([])
} })

test.beforeEach(async ({ page }) => {
  await page.goto('/hu007-t01.html')
  await expect(page.getByRole('heading', { name: 'Pieza personalizada' })).toBeVisible()
})

async function drawAndClose(page, points = pentagon, mode = 'guided') {
  const canvas = page.getByRole('img', { name: /Lienzo del dibujo original/ })
  await expect(page.getByRole('button', { name: 'Cerrar polígono' })).toBeDisabled()
  await canvas.scrollIntoViewIfNeeded()
  for (const [index, point] of points.entries()) {
    // Read the browser's actual transform, including responsive sizing and
    // scrolling. Drawing itself always uses a real mouse click, never events
    // dispatched from page.evaluate or injected component state.
    const position = await canvas.evaluate((svg, [x, y]) => {
      const screen = new DOMPoint(x, y).matrixTransform(svg.getScreenCTM())
      return { x: screen.x, y: screen.y }
    }, point)
    await page.mouse.click(position.x, position.y)
    await expect(page.getByText(`${index + 1} ${index === 0 ? 'vértice' : 'vértices'}`, { exact: true })).toBeVisible()
    if (index < 2) await expect(page.getByRole('button', { name: 'Cerrar polígono' })).toBeDisabled()
  }
  await page.getByRole('button', { name: 'Cerrar polígono' }).click()
  await expect(page.getByText('Polígono cerrado', { exact: true })).toBeVisible()
  if (mode === 'guided') await page.getByRole('combobox').selectOption('guided')
  await expect(page.getByRole('spinbutton')).toHaveCount(points.length)
  for (let id = 1; id <= points.length; id++) {
    await expect(page.getByRole('button', { name: `Seleccionar segmento S${id}`, exact: true })).toHaveText(`S${id}`)
    await expect(field(page, id)).toBeEmpty()
  }
}

async function fill(page, values = lengths) {
  for (const [index, value] of values.entries()) await field(page, index + 1).fill(String(value))
}

for (const sides of [[80,115,63,92,71], [80,115,63,92,71,98]]) {
  test(`${sides.length} lados: fijar hasta n-3 ángulos y liberar para elegir otro vértice`, async ({ page }) => {
    const n=sides.length;
    const points=Array.from({length:n},(_,i)=>[350+180*Math.cos(i*2*Math.PI/n),250+180*Math.sin(i*2*Math.PI/n)]);
    await drawAndClose(page,points,'cyclic'); await fill(page,sides);
    for(let v=2;v<=n-2;v++) await page.getByRole('button',{name:`Fijar ángulo V${v}`,exact:true}).click();
    await expect(page.getByText(`Restricciones de forma: ${n-3} de ${n-3} utilizadas`)).toBeVisible();
    await expect(page.getByRole('button',{name:'Fijar ángulo V1',exact:true})).toBeDisabled();
    const shape=page.getByRole('img',{name:/Vista dimensional completa/}).locator('polygon');
    const before=await shape.getAttribute('points');
    const angle=page.getByRole('spinbutton',{name:/Ángulo interior fijado en V2/});
    await angle.fill(String(Number(await angle.inputValue())-5));
    await expect(shape).not.toHaveAttribute('points',before);
    for(const [i,side] of sides.entries()) await expect(field(page,i+1)).toHaveValue(String(side));
    await page.getByRole('button',{name:'Liberar ángulo V2',exact:true}).click();
    await page.getByRole('button',{name:'Fijar ángulo V1',exact:true}).click();
    await expect(page.getByRole('spinbutton',{name:/Ángulo interior fijado en V1/})).toBeVisible();
    await expect(page.getByText('Geometría convexa validada.',{exact:true})).toBeVisible();
  });
}

test('lados independientes: triángulo 50/70/65 y rechazo de 10/10/30', async ({ page }) => {
  await drawAndClose(page, [[100, 100], [500, 100], [300, 400]], 'cyclic')
  await field(page, 1).fill('50')
  await expect(field(page, 2)).toBeEmpty()
  await fill(page, [50, 70, 65])
  await expect(page.getByRole('region', { name: 'Ángulos interiores' })).toContainText('63,026945°')
  await expect(page.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveText('Geometría convexa validada.')
  await fill(page, [10, 10, 30])
  await expect(page.getByText(/el lado mayor debe ser menor/)).toBeVisible()
  await expect(page.getByRole('img', { name: /Vista dimensional completa/ })).toHaveCount(0)
  await expect(page.getByRole('region', { name: 'Ángulos interiores' })).toHaveCount(0)
})

test('lados independientes: ángulo fijado cambia cuadrilátero sin cambiar lados', async ({ page }) => {
  await drawAndClose(page, [[100, 100], [500, 100], [500, 400], [100, 400]], 'cyclic')
  const sides = [120, 73, 91, 108]
  await fill(page, sides)
  await page.getByRole('combobox').selectOption('angle')
  const angle = page.getByRole('spinbutton', { name: /Ángulo interior fijado/ })
  await angle.fill('85')
  const shape = page.getByRole('img', { name: /Vista dimensional completa/ }).locator('polygon')
  const before = await shape.getAttribute('points')
  await angle.fill('110')
  await expect(shape).not.toHaveAttribute('points', before)
  await expect(angle).toHaveValue('110')
  await expect(page.getByRole('region', { name: 'Ángulos interiores' })).toContainText('Fijado')
  for (const [i, side] of sides.entries()) await expect(field(page, i + 1)).toHaveValue(String(side))
})

test('lados independientes: pentágono irregular con restricción cíclica explícita', async ({ page }) => {
  await drawAndClose(page, pentagon, 'cyclic')
  await fill(page, [80, 115, 63, 92, 71])
  await expect(page.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveText('Geometría convexa validada.')
  await expect(page.getByRole('region', { name: 'Ángulos interiores' }).locator('li')).toHaveCount(5)
  await expect(page.getByText(/circunferencia/)).toBeVisible()
  await expect(page.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})

test('TA-036: longitudes independientes y selección accesible en ambas vistas', async ({ page }) => {
  await drawAndClose(page)
  await expect(page.getByText('0 de 5 medidas ingresadas', { exact: true })).toBeVisible()
  await fill(page)
  await expect(page.getByText('5 de 5 medidas ingresadas', { exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Ángulos interiores' })).toBeVisible()
  await fill(page)
  await expect(page.getByText('5 de 5 medidas ingresadas', { exact: true })).toBeVisible()
  await expect(page.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
  const selection = page.getByRole('button', { name: 'Seleccionar segmento S3', exact: true })
  await selection.click()
  await expect(selection).toHaveAttribute('aria-pressed', 'true')
  await expect(field(page, 3)).toBeFocused()
  await expect(page.getByRole('img', { name: 'Vista dimensional completa. Segmento S3 seleccionado.' })).toBeVisible()
  await field(page, 3).fill('620')
  await expect(field(page, 3)).toHaveValue('620')
  await expect(page.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
  await expect(addButton(page)).toBeDisabled()
  await expect(addButton(page)).toHaveAccessibleDescription('Geometría convexa validada. Agrega la pieza y guarda el pedido para registrarla.')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})

test('TA-036: multiplicar explícitamente todos los lados conserva los ángulos', async ({ page }) => {
  await drawAndClose(page)
  await fill(page)
  const angles = await page.getByRole('region', { name: 'Ángulos interiores' }).textContent()
  await fill(page, lengths.map(value => value * 2))
  await expect(page.getByRole('region', { name: 'Ángulos interiores' })).toHaveText(angles)
  await expect(page.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
})

for (const value of ['0', '-1', '1e']) {
  test(`T02-E03: entrada numérica inválida ${value} muestra error y se recupera`, async ({ page }) => {
    await drawAndClose(page)
    await fill(page)
    await field(page, 1).fill('')
    if (value === '1e') {
      await field(page, 1).pressSequentially(value)
      // Chromium exposes an unfinished exponent as badInput and an empty value.
      expect(await field(page, 1).evaluate((input) => input.validity.badInput)).toBe(true)
    } else await field(page, 1).fill(value)
    await field(page, 1).press('Tab')
    await expect(field(page, 1)).toHaveAttribute('aria-invalid', 'true')
    await expect(field(page, 1)).toHaveAccessibleDescription('Usa un número finito mayor que 0.')
    await expect(page.getByText('4 de 5 medidas ingresadas', { exact: true })).toBeVisible()
    await expect(page.getByRole('img', { name: /Vista dimensional/ })).toHaveCount(0)
    await expect(addButton(page)).toBeDisabled()
    await field(page, 1).fill('850')
    await expect(field(page, 1)).toHaveAttribute('aria-invalid', 'false')
    await expect(page.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
  })
}

test('T01-T02-E04: deshacer y reiniciar invalidan las medidas del borrador', async ({ page }) => {
  await drawAndClose(page)
  await fill(page)
  await page.getByRole('button', { name: 'Seleccionar segmento S5', exact: true }).click()
  await page.getByRole('button', { name: 'Deshacer último vértice' }).click()
  await expect(page.getByText('Polígono abierto', { exact: true })).toBeVisible()
  await expect(page.getByText('4 vértices', { exact: true })).toBeVisible()
  await expect(page.getByRole('spinbutton')).toHaveCount(0)
  await expect(page.getByRole('img', { name: /Vista dimensional/ })).toHaveCount(0)
  await page.getByRole('button', { name: 'Cerrar polígono' }).click()
  await expect(page.getByText('0 de 4 medidas ingresadas', { exact: true })).toBeVisible()
  for (let id = 1; id <= 4; id++) await expect(field(page, id)).toBeEmpty()
  await field(page, 1).fill('850')
  await page.getByRole('button', { name: 'Reiniciar dibujo' }).click()
  await expect(page.getByText('0 vértices', { exact: true })).toBeVisible()
  for (const name of ['Cerrar polígono', 'Deshacer último vértice', 'Reiniciar dibujo']) {
    await expect(page.getByRole('button', { name })).toBeDisabled()
  }
  await expect(page.getByRole('spinbutton')).toHaveCount(0)
  await expect(page.getByRole('button', { pressed: true })).toHaveCount(0)
  await expect(page.getByRole('img', { name: /Vista dimensional/ })).toHaveCount(0)
})

test('T03-E05: dimensiones completas validan convexidad automáticamente y borrar retira el éxito', async ({ page }) => {
  const validation = page.getByRole('status', { name: 'Resultado de validación geométrica' })
  await expect(validation).toHaveText('Pendiente de completar dimensiones.')
  await drawAndClose(page)
  await fill(page)
  await expect(validation).toHaveText('Geometría convexa validada.')
  await expect(validation).toBeVisible()
  await expect(addButton(page)).toBeDisabled()
  await expect(page.getByText('Agrega la pieza y guarda el pedido para registrarla.', { exact: true })).toBeVisible()
  await field(page, 1).fill('')
  await expect(validation).toHaveText('Pendiente de completar dimensiones.')
  await field(page, 1).fill('850')
  await expect(validation).toHaveText('Geometría convexa validada.')
})

test('TA-036: escalar un contorno cóncavo conserva su rechazo', async ({ page }) => {
  await drawAndClose(page, [[100, 100], [500, 100], [260, 280], [500, 460], [100, 460]])
  await fill(page, [400, 300, 300, 400, 360])
  await expect(page.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
  const rejection = page.getByRole('alert', { name: 'Resultado de validación geométrica' })
  await expect(rejection).toHaveText('La figura resultante no es convexa.')
  await expect(rejection).toBeVisible()
  await expect(addButton(page)).toBeDisabled()
  await field(page, 2).fill('700')
  await expect(page.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
  await expect(rejection).toHaveText('La figura resultante no es convexa.')
  await expect(rejection).not.toContainText(/cross|epsilon|determinant|stack/i)
  await expect(field(page, 2)).toHaveValue('700')
  await expect(addButton(page)).toBeDisabled()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})

test('T03-E07: bow-tie simétrico completo se rechaza por autointersección', async ({ page }) => {
  await drawAndClose(page, [[100, 50], [400, 450], [100, 450], [400, 50]])
  await fill(page, [500, 300, 500, 300])
  await expect(page.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
  await expect(page.getByRole('alert', { name: 'Resultado de validación geométrica' })).toHaveText('La geometría se intersecta consigo misma.')
  await expect(addButton(page)).toBeDisabled()
  await expect(page.getByText('Geometría convexa validada.', { exact: true })).toHaveCount(0)
})

test('T03-E08: regresión de descripción accesible conserva el motivo actual del bloqueo', async ({ page }) => {
  await expect(addButton(page)).toHaveAccessibleDescription('Pendiente de completar dimensiones. Agrega la pieza y guarda el pedido para registrarla.')
  await drawAndClose(page)
  await fill(page)
  await expect(addButton(page)).toHaveAccessibleDescription('Geometría convexa validada. Agrega la pieza y guarda el pedido para registrarla.')
  await page.getByRole('button', { name: 'Reiniciar dibujo' }).click()
  await drawAndClose(page, [[100, 100], [500, 100], [260, 280], [500, 460], [100, 460]])
  await fill(page, [400, 300, 300, 400, 360])
  await expect(addButton(page)).toHaveAccessibleDescription('La figura resultante no es convexa. Agrega la pieza y guarda el pedido para registrarla.')
  await expect(addButton(page)).toBeDisabled()
})
