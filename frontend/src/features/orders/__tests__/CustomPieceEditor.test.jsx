import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, test } from 'vitest'
import CustomPieceEditor from '../CustomPieceEditor'

const pentagon = [[200, 50], [500, 50], [600, 250], [350, 450], [100, 250]]
const lengths = [850, 420, 600, 510, 730]
const canvas = () => screen.getByRole('img', { name: /Lienzo del dibujo original/ })
const field = (id) => screen.getByRole('spinbutton', { name: `Longitud del segmento S${id} en milímetros` })
const selector = (id) => screen.getByRole('button', { name: `Seleccionar segmento S${id}` })
const button = (name) => screen.getByRole('button', { name })

function setup() {
  const user = userEvent.setup()
  render(<CustomPieceEditor />)
  return user
}

async function draw(user, points = pentagon) {
  for (const [x, y] of points) {
    await user.pointer({ target: canvas(), keys: '[MouseLeft]', coords: { clientX: x, clientY: y } })
  }
}

async function close(user) {
  await draw(user)
  await user.click(button('Cerrar polígono'))
}

async function fill(user, values = lengths) {
  for (const [index, value] of values.entries()) {
    await user.clear(field(index + 1))
    await user.type(field(index + 1), String(value))
  }
}

function expectInitial() {
  expect(screen.getByText('Polígono abierto')).toBeVisible()
  expect(screen.getByText('0 vértices')).toBeVisible()
  for (const name of ['Cerrar polígono', 'Deshacer último vértice', 'Reiniciar dibujo']) {
    expect(button(name)).toBeDisabled()
  }
  expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Seleccionar segmento/ })).not.toBeInTheDocument()
  expect(screen.queryByRole('img', { name: /Vista dimensional/ })).not.toBeInTheDocument()
  // SVG primitives have no accessible roles: inspect the rendered drawing only.
  expect(canvas().querySelectorAll('circle, polygon, line')).toHaveLength(0)
  expect(canvas().querySelector('polyline')).toHaveAttribute('points', '')
}

describe('HU-007 T01 — dibujo y controles (caja negra)', () => {
  test('T01-C01: editor inicial visible, accesible y sin dimensiones', () => {
    setup()
    expect(screen.getByRole('region', { name: 'Pieza personalizada' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Dibujo original' })).toBeVisible()
    expect(screen.getByRole('group', { name: 'Herramientas de dibujo' })).toBeVisible()
    expect(canvas()).toHaveAccessibleDescription(/Faltan 3 vértices/)
    expect(screen.getByText(/Se pierde al salir o recargar/)).toBeVisible()
    expectInitial()
  })

  test('T01-C02: clics crean vértices ordenados y segmentos; cerrar exige tres', async () => {
    const user = setup()
    const points = pentagon.slice(0, 3)
    for (let count = 1; count <= 3; count++) {
      await draw(user, [points[count - 1]])
      expect(screen.getByText(`${count} ${count === 1 ? 'vértice' : 'vértices'}`)).toBeVisible()
      expect(canvas().querySelectorAll('circle')).toHaveLength(count)
      expect(canvas().querySelector('polyline')).toHaveAttribute('points', points.slice(0, count).map((p) => p.join(',')).join(' '))
      expect(canvas().querySelector('polygon')).toBeNull()
      expect(button('Deshacer último vértice')).toBeEnabled()
      expect(button('Reiniciar dibujo')).toBeEnabled()
      if (count < 3) {
        expect(button('Cerrar polígono')).toBeDisabled()
        await user.click(button('Cerrar polígono'))
        expect(screen.getByText('Polígono abierto')).toBeVisible()
      } else expect(button('Cerrar polígono')).toBeEnabled()
    }
    await user.click(button('Cerrar polígono'))
    expect(screen.getByText('Polígono cerrado')).toBeVisible()
    expect(canvas().querySelector('polygon')).toHaveAttribute('points', points.map((p) => p.join(',')).join(' '))
    expect(screen.getAllByRole('spinbutton')).toHaveLength(3)
  })

  test('T01-C03: cerrar bloquea clics adicionales sin cambiar el contorno', async () => {
    const user = setup()
    await close(user)
    const original = canvas().querySelector('polygon').getAttribute('points')
    await draw(user, [[250, 200], [400, 350]])
    expect(screen.getByText('5 vértices')).toBeVisible()
    expect(canvas().querySelector('polygon')).toHaveAttribute('points', original)
    expect(screen.getByText('Polígono cerrado')).toBeVisible()
    expect(screen.getByText('Contorno cerrado')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Cerrar polígono' })).not.toBeInTheDocument()
    expect(button('Deshacer último vértice')).toBeEnabled()
    expect(button('Reiniciar dibujo')).toBeEnabled()
  })

  test('T01-C04: deshacer abierto elimina el último punto hasta volver al inicio', async () => {
    const user = setup()
    await draw(user, pentagon.slice(0, 3))
    for (const remaining of [2, 1, 0]) {
      await user.click(button('Deshacer último vértice'))
      expect(canvas().querySelector('polyline')).toHaveAttribute('points', pentagon.slice(0, remaining).map((p) => p.join(',')).join(' '))
      expect(button('Cerrar polígono')).toBeDisabled()
    }
    expectInitial()
    expect(screen.getByRole('heading', { name: 'Dibujo original' })).toHaveFocus()
  })

  test('T01-C05: deshacer cerrado reabre, elimina el último punto y permite dibujar', async () => {
    const user = setup()
    await close(user)
    await user.click(button('Deshacer último vértice'))
    expect(screen.getByText('Polígono abierto')).toBeVisible()
    expect(screen.getByText('4 vértices')).toBeVisible()
    expect(canvas().querySelector('polyline')).toHaveAttribute('points', pentagon.slice(0, 4).map((p) => p.join(',')).join(' '))
    expect(button('Cerrar polígono')).toBeEnabled()
    await draw(user, [[150, 200]])
    await user.click(button('Cerrar polígono'))
    expect(screen.getByText('5 vértices')).toBeVisible()
    expect(screen.getByText('Polígono cerrado')).toBeVisible()
  })

  test.each([false, true])('T01-C06: reiniciar limpia el dibujo (cerrado=%s)', async (closed) => {
    const user = setup()
    await draw(user)
    if (closed) await user.click(button('Cerrar polígono'))
    await user.click(button('Reiniciar dibujo'))
    expectInitial()
    await draw(user, [[100, 100]])
    expect(screen.getByText('1 vértice')).toBeVisible()
    expect(button('Reiniciar dibujo')).toBeEnabled()
  })
})

describe('HU-007 T02 — dimensiones y selección (caja negra)', () => {
  test('T02-C01: cinco lados S1…S5 vacíos, progreso cero y sin escala física', async () => {
    const user = setup()
    await close(user)
    expect(screen.getAllByRole('spinbutton')).toHaveLength(5)
    for (let id = 1; id <= 5; id++) {
      expect(selector(id)).toHaveTextContent(`S${id}`)
      expect(field(id)).toHaveValue(null)
      expect(field(id)).toHaveAttribute('step', 'any')
      expect(field(id)).toBeRequired()
    }
    expect(screen.getByText('0 de 5 medidas ingresadas')).toBeVisible()
    expect(screen.getByText(/Sin escala física. Ingresa una primera medida/)).toBeVisible()
    expect(screen.queryByRole('spinbutton', { name: /ancho|alto/i })).not.toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Vista dimensional provisional/ })).toBeVisible()
  })

  test('T02-C02: una medida deja preview provisional y cuatro campos pendientes vacíos', async () => {
    const user = setup()
    await close(user)
    await user.type(field(1), '850')
    expect(screen.getByText('1 de 5 medidas ingresadas')).toBeVisible()
    for (let id = 2; id <= 5; id++) expect(field(id)).toHaveValue(null)
    await user.click(selector(3))
    expect(screen.getByText(/Estimación provisional/)).toBeVisible()
    expect(screen.getByRole('img', { name: /Vista dimensional provisional/ })).toBeVisible()
    expect(screen.queryByText('Vista dimensional completa')).not.toBeInTheDocument()
  })

  test('T02-C03: selección S1→S3→S5 sincroniza ambos SVG sin perder medidas', async () => {
    const user = setup()
    await close(user)
    await user.type(field(1), '850')
    for (const id of [1, 3, 5]) {
      await user.click(selector(id))
      expect(screen.getAllByRole('button', { pressed: true })).toEqual([selector(id)])
      expect(field(id)).toHaveFocus()
      const preview = screen.getByRole('img', { name: `Vista dimensional provisional. Segmento S${id} seleccionado.` })
      // Overlays are aria-hidden; verify their visible selection markers directly.
      for (const view of [canvas(), preview]) {
        expect(view.querySelectorAll('line[data-active="true"]')).toHaveLength(1)
        expect(view.querySelectorAll('line')[id - 1]).toHaveAttribute('data-active', 'true')
        expect(view.querySelector('text[data-active="true"]')).toHaveTextContent(`S${id}`)
      }
      expect(field(1)).toHaveValue(850)
    }
  })

  test('T02-C04: editar una medida recalcula preview y conserva boceto y otros campos', async () => {
    const user = setup()
    await close(user)
    await fill(user)
    const sketch = canvas().querySelector('polygon').getAttribute('points')
    const preview = screen.getByRole('img', { name: /Vista dimensional completa/ })
    const before = preview.querySelector('polygon').getAttribute('points')
    await user.clear(field(1))
    await user.type(field(1), '900')
    expect(screen.getByRole('img', { name: /Vista dimensional completa/ }).querySelector('polygon').getAttribute('points')).not.toBe(before)
    expect(canvas().querySelector('polygon')).toHaveAttribute('points', sketch)
    expect(field(1)).toHaveValue(900)
    for (let id = 2; id <= 5; id++) expect(field(id)).toHaveValue(lengths[id - 1])
  })

  test('T02-C05: dimensiones completas mantienen Agregar deshabilitado por registro pendiente', async () => {
    const user = setup()
    await close(user)
    await fill(user)
    expect(screen.getByText('5 de 5 medidas ingresadas')).toBeVisible()
    expect(screen.getByText('Vista dimensional completa')).toBeVisible()
    expect(screen.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expect(button('Agregar pieza al pedido')).toHaveAccessibleDescription('Geometría convexa validada. El registro de piezas en el pedido aún no está disponible.')
  })

  test('T02-C06: longitudes 1000/100/100/100/100 informan imposibilidad sin convexidad', async () => {
    const user = setup()
    await close(user)
    await fill(user, [1000, 100, 100, 100, 100])
    expect(screen.getByRole('alert')).toHaveTextContent('Las longitudes ingresadas no permiten formar un polígono cerrado.')
    expect(screen.getByRole('alert')).not.toHaveTextContent(/convex/i)
    expect(screen.queryByRole('img', { name: /Vista dimensional/ })).not.toBeInTheDocument()
    expect(screen.queryByText('Vista dimensional completa')).not.toBeInTheDocument()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
  })

  test.each(['0', '-1'])('T02-C07: longitud inválida %s da error visible y accesible', async (value) => {
    const user = setup()
    await close(user)
    await user.type(field(1), value)
    await user.tab()
    expect(field(1)).toHaveAttribute('aria-invalid', 'true')
    expect(field(1)).toHaveAccessibleDescription('Usa un número finito mayor que 0.')
    expect(screen.getByText('0 de 5 medidas ingresadas')).toBeVisible()
    expect(screen.getByText(/Revisa las medidas marcadas/)).toBeVisible()
    expect(screen.queryByRole('img', { name: /Vista dimensional/ })).not.toBeInTheDocument()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
  })

  test('T02-C08: decimal positivo menor que 0.01 es aceptado sin mínimo artificial', async () => {
    const user = setup()
    await close(user)
    await user.type(field(1), '0.001')
    expect(field(1)).toHaveValue(0.001)
    expect(field(1)).toHaveAttribute('aria-invalid', 'false')
    expect(screen.getByText('1 de 5 medidas ingresadas')).toBeVisible()
    expect(screen.getByRole('img', { name: /Vista dimensional provisional/ })).toBeVisible()
  })

  test('T02-C09: borrar una medida completa vuelve a provisional; borrar todas quita escala', async () => {
    const user = setup()
    await close(user)
    await fill(user)
    await user.clear(field(3))
    expect(screen.getByText('4 de 5 medidas ingresadas')).toBeVisible()
    expect(field(3)).toHaveValue(null)
    expect(screen.getByRole('img', { name: /Vista dimensional provisional/ })).toBeVisible()
    for (const id of [1, 2, 4, 5]) await user.clear(field(id))
    expect(screen.getByText('0 de 5 medidas ingresadas')).toBeVisible()
    expect(screen.getByText(/Sin escala física. Ingresa una primera medida/)).toBeVisible()
  })

  test('T02-C10: deshacer invalida medidas, selección y preview; recierre crea lados vacíos', async () => {
    const user = setup()
    await close(user)
    await fill(user)
    await user.click(selector(5))
    await user.click(button('Deshacer último vértice'))
    expect(screen.getByText('4 vértices')).toBeVisible()
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { pressed: true })).not.toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /Vista dimensional/ })).not.toBeInTheDocument()
    await user.click(button('Cerrar polígono'))
    expect(screen.getAllByRole('spinbutton')).toHaveLength(4)
    for (let id = 1; id <= 4; id++) expect(field(id)).toHaveValue(null)
    expect(screen.getByText('0 de 4 medidas ingresadas')).toBeVisible()
    expect(selector(1)).toHaveAttribute('aria-pressed', 'true')
  })

  test('T02-C11: reiniciar con medidas limpia todo y un nuevo dibujo no conserva selección', async () => {
    const user = setup()
    await close(user)
    await fill(user)
    await user.click(selector(5))
    await user.click(button('Reiniciar dibujo'))
    expectInitial()
    await close(user)
    expect(screen.getByText('0 de 5 medidas ingresadas')).toBeVisible()
    for (let id = 1; id <= 5; id++) expect(field(id)).toHaveValue(null)
    expect(selector(1)).toHaveAttribute('aria-pressed', 'true')
  })

  test('T02-C12: cierre y selección por teclado dirigen el foco a controles etiquetados', async () => {
    const user = setup()
    await draw(user)
    await user.tab()
    await user.tab()
    await user.tab()
    expect(button('Cerrar polígono')).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(field(1)).toHaveFocus()
    await user.tab()
    expect(selector(2)).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(field(2)).toHaveFocus()
    expect(selector(2)).toHaveAttribute('aria-pressed', 'true')
    expect(within(screen.getByRole('region', { name: 'Dimensiones por segmento' })).getAllByRole('spinbutton')).toHaveLength(5)
  })
})

describe('HU-007 T03 — validación geométrica derivada (caja negra)', () => {
  const concave = [[100, 100], [500, 100], [260, 280], [500, 460], [100, 460]]
  const concaveLengths = [400, 300, 300, 400, 360]
  const validation = (role = 'status') => screen.getByRole(role, { name: 'Resultado de validación geométrica' })

  async function dimensionConcave(user) {
    await draw(user, concave)
    await user.click(button('Cerrar polígono'))
    await fill(user, concaveLengths)
  }

  test('T03-C01: pendiente antes de cerrar y mientras hay longitudes estimadas', async () => {
    const user = setup()
    expect(validation()).toHaveTextContent('Pendiente de completar dimensiones.')
    await close(user)
    await user.type(field(1), '850')
    expect(screen.getByRole('img', { name: /Vista dimensional provisional/ })).toBeVisible()
    expect(validation()).toHaveTextContent('Pendiente de completar dimensiones.')
    expect(screen.queryByText('Geometría convexa validada.')).not.toBeInTheDocument()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
  })

  test('T03-C02: geometría completa convexa informa éxito accesible sin habilitar registro', async () => {
    const user = setup()
    await close(user)
    await fill(user)
    expect(validation()).toHaveTextContent('Geometría convexa validada.')
    expect(validation()).toHaveAttribute('aria-atomic', 'true')
    expect(validation()).toBeVisible()
    expect(screen.queryByRole('button', { name: /^Validar/ })).not.toBeInTheDocument()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expect(screen.getByText('El registro de piezas en el pedido aún no está disponible.')).toBeVisible()
  })

  test('T03-C03: geometría completa cóncava muestra rechazo y conserva medidas', async () => {
    const user = setup()
    await dimensionConcave(user)
    expect(screen.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
    expect(validation('alert')).toHaveTextContent('La figura resultante no es convexa.')
    expect(validation('alert')).toBeVisible()
    expect(validation('alert')).toHaveAttribute('aria-atomic', 'true')
    expect(validation('alert')).not.toHaveTextContent(/epsilon|determinant|cross|stack/i)
    for (let id = 1; id <= 5; id++) expect(field(id)).toHaveValue(concaveLengths[id - 1])
    expect(button('Agregar pieza al pedido')).toBeDisabled()
  })

  test('T03-C04: bow-tie completo se anuncia como autointersección, no área nula', async () => {
    const user = setup()
    await draw(user, [[100, 100], [400, 500], [100, 500], [400, 100]])
    await user.click(button('Cerrar polígono'))
    await fill(user, [500, 300, 500, 300])
    expect(screen.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
    expect(validation('alert')).toHaveTextContent('La geometría se intersecta consigo misma.')
    expect(button('Agregar pieza al pedido')).toBeDisabled()
  })

  test('T03-C05: editar S2 recalcula concavidad→cruce→concavidad sin resultado obsoleto', async () => {
    const user = setup()
    await dimensionConcave(user)
    expect(validation('alert')).toHaveTextContent('La figura resultante no es convexa.')
    await user.clear(field(2))
    expect(validation()).toHaveTextContent('Pendiente de completar dimensiones.')
    await user.type(field(2), '700')
    expect(screen.getByRole('img', { name: /Vista dimensional completa/ })).toBeVisible()
    expect(validation('alert')).toHaveTextContent('La geometría se intersecta consigo misma.')
    await user.clear(field(2))
    await user.type(field(2), '300')
    expect(validation('alert')).toHaveTextContent('La figura resultante no es convexa.')
    for (const id of [1, 3, 4, 5]) expect(field(id)).toHaveValue(concaveLengths[id - 1])
  })

  test('T03-C06: borrar o invalidar medidas retira VALID y corregir vuelve a validar', async () => {
    const user = setup()
    await close(user)
    await fill(user)
    expect(validation()).toHaveTextContent('Geometría convexa validada.')
    await user.clear(field(1))
    expect(validation()).toHaveTextContent('Pendiente de completar dimensiones.')
    await user.type(field(1), '10000')
    expect(screen.queryByRole('img', { name: /Vista dimensional completa/ })).not.toBeInTheDocument()
    expect(validation()).toHaveTextContent('Pendiente de completar dimensiones.')
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    await user.clear(field(1))
    await user.type(field(1), '850')
    expect(validation()).toHaveTextContent('Geometría convexa validada.')
  })

  test.each(['Deshacer último vértice', 'Reiniciar dibujo'])('T03-C07: %s invalida el éxito previo', async (action) => {
    const user = setup()
    await close(user)
    await fill(user)
    expect(validation()).toHaveTextContent('Geometría convexa validada.')
    await user.click(button(action))
    expect(validation()).toHaveTextContent('Pendiente de completar dimensiones.')
    expect(screen.queryByText('Geometría convexa validada.')).not.toBeInTheDocument()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
  })
})
