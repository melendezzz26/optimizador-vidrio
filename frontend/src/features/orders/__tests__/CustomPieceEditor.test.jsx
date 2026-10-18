// Regression suite adapted to explicit independent lengths and a sketch initial guess.
import { render, screen, fireEvent, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import CustomPieceEditor from '../CustomPieceEditor'

const pentagon = [[200, 50], [500, 50], [600, 250], [350, 450], [100, 250]]
const canvas = () => screen.getByRole('img', { name: /Lienzo del dibujo original|Vista dimensional de la pieza/ })
const field = (id) => screen.getByRole('spinbutton', { name: `Longitud del segmento S${id} en milímetros` })
const selector = (id) => screen.getByRole('button', { name: `Seleccionar segmento S${id}` })
const button = (name) => screen.getByRole('button', { name })

function setup() {
  const user = userEvent.setup()
  render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} />)
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

function expectInitial() {
  expect(canvas()).toHaveAttribute('data-closed', 'false')
  expect(screen.getByText(/Faltan 3 vértices/)).toBeVisible()
  for (const name of ['Cerrar polígono', 'Deshacer', 'Reiniciar']) {
    expect(button(name)).toBeDisabled()
  }
  expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Seleccionar segmento/ })).not.toBeInTheDocument()
  expect(canvas().querySelector('polygon[data-provisional="false"]')).toBeNull()
  // SVG primitives have no accessible roles: inspect the rendered drawing only.
  expect(canvas().querySelectorAll('circle, polygon, line')).toHaveLength(0)
  expect(canvas().querySelector('polyline')).toHaveAttribute('points', '')
  expect(screen.queryByRole('status', { name: 'Resultado de validación geométrica' })).not.toBeInTheDocument()
}

describe('HU-007 T01 — dibujo y controles (caja negra)', () => {
  test('T01-C01: editor inicial visible, accesible y sin dimensiones', () => {
    setup()
    expect(screen.getByRole('region', { name: 'Pieza personalizada' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Paso 1: Dibujar contorno' })).toBeVisible()
    expect(screen.getByRole('group', { name: 'Herramientas de dibujo' })).toBeVisible()
    expect(canvas()).toHaveAccessibleName('Lienzo del dibujo original')
    expect(screen.getByText(/Haz clic en el lienzo vacío/)).toBeVisible()
    expectInitial()
  })

  test('T01-C02: clics crean vértices ordenados y segmentos; cerrar exige tres', async () => {
    const user = setup()
    const points = pentagon.slice(0, 3)
    for (let count = 1; count <= 3; count++) {
      await draw(user, [points[count - 1]])
      expect(screen.getByText(`Faltan ${Math.max(0, 3 - count)} vértices`)).toBeVisible()
      expect(canvas().querySelectorAll('circle')).toHaveLength(count)
      expect(canvas().querySelector('polyline')).toHaveAttribute('points', points.slice(0, count).map((p) => p.join(',')).join(' '))
      expect(canvas().querySelector('polygon')).toBeNull()
      expect(button('Deshacer')).toBeEnabled()
      expect(button('Reiniciar')).toBeEnabled()
      if (count < 3) {
        expect(button('Cerrar polígono')).toBeDisabled()
        await user.click(button('Cerrar polígono'))
        expect(canvas()).toHaveAttribute('data-closed', 'false')
      } else expect(button('Cerrar polígono')).toBeEnabled()
    }
    await user.click(button('Cerrar polígono'))
    expect(canvas()).toHaveAttribute('data-closed', 'true')
    expect(canvas().querySelector('polygon').getAttribute('points').split(' ')).toHaveLength(3)
    expect(screen.getAllByRole('spinbutton')).toHaveLength(3)
  })

  test('T01-C03: cerrar bloquea clics adicionales sin cambiar el contorno', async () => {
    const user = setup()
    await close(user)
    const original = canvas().querySelector('polygon').getAttribute('points')
    await draw(user, [[250, 200], [400, 350]])
    expect(canvas().querySelector('polygon').getAttribute('points').split(' ')).toHaveLength(5)
    expect(canvas().querySelector('polygon')).toHaveAttribute('points', original)
    expect(canvas()).toHaveAttribute('data-closed', 'true')
    expect(screen.getByText('Boceto provisional')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Cerrar polígono' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Deshacer' })).not.toBeInTheDocument()
    expect(button('Reiniciar')).toBeEnabled()
  })

  test('T01-C04: deshacer abierto elimina el último punto hasta volver al inicio', async () => {
    const user = setup()
    await draw(user, pentagon.slice(0, 3))
    for (const remaining of [2, 1, 0]) {
      await user.click(button('Deshacer'))
      expect(canvas().querySelector('polyline')).toHaveAttribute('points', pentagon.slice(0, remaining).map((p) => p.join(',')).join(' '))
      expect(button('Cerrar polígono')).toBeDisabled()
    }
    expectInitial()
    expect(button('Cerrar polígono')).toBeDisabled()
  })

  test('T01-C05: cerrado protege el contorno; reiniciar permite dibujar otra figura', async () => {
    const user = setup()
    await close(user)
    expect(screen.queryByRole('button', { name: 'Deshacer' })).not.toBeInTheDocument()
    await user.click(button('Reiniciar'))
    expectInitial()
    await draw(user, pentagon.slice(0, 4))
    await user.click(button('Cerrar polígono'))
    expect(canvas().querySelector('polygon').getAttribute('points').split(' ')).toHaveLength(4)
  })

  test.each([false, true])('T01-C06: reiniciar limpia el dibujo (cerrado=%s)', async (closed) => {
    const user = setup()
    await draw(user)
    if (closed) await user.click(button('Cerrar polígono'))
    await user.click(button('Reiniciar'))
    expectInitial()
    await draw(user, [[100, 100]])
    expect(canvas().querySelectorAll('circle')).toHaveLength(1)
    expect(button('Reiniciar')).toBeEnabled()
  })
})

describe('TA-036: regresiones vigentes del editor', () => {
  const measure = (id, value) => {
    // Enter every still-empty side explicitly; the production editor never fills other fields.
    const points = canvas().querySelector('polygon').getAttribute('points').split(' ').map(p => p.split(',').map(Number));
    const sides = points.map((p,i) => Math.hypot(points[(i+1)%points.length][0]-p[0], points[(i+1)%points.length][1]-p[1]));
    if (Number(value)>0 && sides[id-1]>0) sides.forEach((side,i) => { if (i!==id-1 && field(i+1).value==='') fireEvent.change(field(i+1), { target: { value: String(side * Number(value) / sides[id-1]) } }); });
    fireEvent.change(field(id), { target: { value: String(value) } });
  }

  function expectSynchronized(id) {
    expect(selector(id)).toHaveAttribute('aria-pressed', 'true')
    const view = canvas()
    expect(view.querySelectorAll('line[data-active="true"]')).toHaveLength(1)
    expect(view.querySelectorAll('line')[id - 1]).toHaveAttribute('data-active', 'true')
    expect(view.querySelector('text[data-active="true"]')).toHaveTextContent(`S${id}`)
  }

  test('cierre identifica todos los campos requeridos sin escala física ni geometría guardable', async () => {
    const user = setup()
    await close(user)
    for (let id = 1; id <= 5; id++) {
      expect(field(id)).toHaveValue(null)
      expect(field(id)).toBeRequired()
      expect(field(id)).toHaveAttribute('step', 'any')
    }
    expect(screen.getByText('0 / 5 completados')).toBeVisible()
    expect(screen.getByText(/Ingresa las medidas de cada lado/)).toBeVisible()
    expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('Vista provisional:')
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expectSynchronized(1, 'Vista dimensional provisional. Segmento S1 seleccionado.')
  })

  test('selección y hover conservan arista y etiqueta sincronizadas en el lienzo único sin alterar medidas', async () => {
    const user = setup()
    await close(user)
    for (const scaled of [false, true]) {
      if (scaled) measure(1, 850)
      const values = screen.getAllByRole('spinbutton').map(input => input.value)
      for (const id of [1, 3, 5]) {
        await user.click(selector(id))
        expect(field(id)).toHaveFocus()
        const name = `Vista dimensional ${scaled ? 'completa' : 'provisional'}. Segmento S${id} seleccionado.`
        expectSynchronized(id, name)
        // Hover is not a selection action in the current editor.
        await user.hover(selector(id === 5 ? 2 : 5))
        await user.hover(canvas().querySelectorAll('line')[0])
        expectSynchronized(id, name)
        expect(screen.getAllByRole('spinbutton').map(input => input.value)).toEqual(values)
      }
    }
  })

  test('longitud 0.001 válida produce vértices pequeños y conserva ángulos y validación', async () => {
    const onSave = vi.fn()
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={onSave} />)
    await draw(user, [[100, 100], [500, 100], [500, 300], [100, 300]])
    await user.click(button('Cerrar polígono'))
    measure(1, 0.001)
    expect(field(1)).toHaveValue(0.001)
    expect(field(2)).toHaveValue(0.0005)
    expect(field(1)).toHaveAttribute('aria-invalid', 'false')
    expect(canvas().querySelector('.custom-piece-editor__vertex-label')).toHaveTextContent('V1 (90°)')
    expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('✓ Geometría validada y lista.')
    await user.click(button('Agregar pieza al pedido'))
    const vertices = onSave.mock.calls[0][0].vertices
    const expected = [[0, 0], [0.001, 0], [0.001, 0.0005], [0, 0.0005]]
    vertices.forEach((point, i) => point.forEach((value, axis) => expect(value).toBeCloseTo(expected[i][axis], 12)))
  })

  test('reiniciar una figura dimensionada invalida el resultado y recerrar crea campos vacíos', async () => {
    const user = setup()
    await close(user)
    measure(1, 850)
    await user.click(selector(5))
    expect(button('Agregar pieza al pedido')).toBeEnabled()
    await user.click(button('Reiniciar'))
    expectInitial()
    await draw(user, pentagon.slice(0, 4))
    await user.click(button('Cerrar polígono'))
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expect(screen.getAllByRole('spinbutton')).toHaveLength(4)
    screen.getAllByRole('spinbutton').forEach(input => expect(input).toHaveValue(null))
    expectSynchronized(1)
  })

  test('reiniciar después de medir elimina escala y selección antes del siguiente dibujo', async () => {
    const user = setup()
    await close(user)
    measure(1, 850)
    await user.click(selector(5))
    await user.click(button('Reiniciar'))
    expectInitial()
    await close(user)
    screen.getAllByRole('spinbutton').forEach(input => expect(input).toHaveValue(null))
    expectSynchronized(1, 'Vista dimensional provisional. Segmento S1 seleccionado.')
    expect(canvas().querySelector('.custom-piece-editor__vertex-label')).not.toHaveTextContent('°')
  })

  test('borrar todas las medidas retira escala, ángulos y resultado válido anterior', async () => {
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={vi.fn()} />)
    await close(user)
    measure(1, 850)
    for (let id = 1; id <= 5; id++) await user.clear(field(id))
    expect(screen.getByText('0 / 5 completados')).toBeVisible()
    expect(screen.getByText(/Ingresa las medidas de cada lado/)).toBeVisible()
    expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('Vista provisional:')
    expect(canvas().querySelector('.custom-piece-editor__vertex-label')).not.toHaveTextContent('°')
    expect(button('Agregar pieza al pedido')).toBeDisabled()
  })

  test('geometría completa no autoriza guardar sin material de pedido válido', async () => {
    const onSave = vi.fn()
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={onSave} headerReady={false} />)
    await close(user)
    measure(1, 850)
    expect(screen.getByText('✓ Geometría validada y lista.')).toBeVisible()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expect(button('Agregar pieza al pedido')).toHaveAccessibleDescription(/Selecciona el tipo de vidrio y el espesor/)
    await user.click(button('Agregar pieza al pedido'))
    expect(onSave).not.toHaveBeenCalled()
  })

  test('vértices consecutivos repetidos muestran error de dibujo sin guardar geometría degenerada', async () => {
    const onSave = vi.fn()
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={onSave} />)
    await draw(user, [[100, 100], [400, 100], [400, 100], [100, 300]])
    await user.click(button('Cerrar polígono'))
    expect(screen.getByText(/lados superpuestos|área insuficiente/)).toBeVisible()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expect(onSave).not.toHaveBeenCalled()
  })

  test('selección por foco directo se refleja en líneas y etiquetas del lienzo único', async () => {
    const user = setup()
    await close(user)
    measure(1, 850)
    await user.click(field(4))
    expectSynchronized(4, 'Vista dimensional completa. Segmento S4 seleccionado.')
    expect(within(screen.getByRole('region', { name: 'Pieza personalizada' })).getAllByRole('spinbutton')).toHaveLength(5)
  })

  test('invalidar y corregir una dimensión retira y recalcula la validación sin geometría obsoleta', async () => {
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={vi.fn()} />)
    await close(user)
    measure(1, 850)
    expect(button('Agregar pieza al pedido')).toBeEnabled()
    measure(1, 0)
    expect(field(1)).toHaveAttribute('aria-invalid', 'true')
    expect(screen.queryByText('✓ Geometría validada y lista.')).not.toBeInTheDocument()
    expect(canvas().querySelector('polygon[data-provisional="false"]')).toBeNull()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    measure(1, 900)
    expect(screen.getByText('✓ Geometría validada y lista.')).toBeVisible()
    expect(field(1)).toHaveValue(900)
    expect(button('Agregar pieza al pedido')).toBeEnabled()
    await user.clear(field(1))
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('Vista provisional:')
    measure(1, 850)
    expect(screen.getByText('✓ Geometría validada y lista.')).toBeVisible()
    expect(button('Agregar pieza al pedido')).toBeEnabled()
  })
})

describe('TA-036: vértices canónicos, escala y ángulos', () => {
  const rectangle = [[100, 100], [500, 100], [500, 300], [100, 300]]
  const measure = (id, value) => {
    // Enter every still-empty side explicitly; the production editor never fills other fields.
    const points = canvas().querySelector('polygon').getAttribute('points').split(' ').map(p => p.split(',').map(Number));
    const sides = points.map((p,i) => Math.hypot(points[(i+1)%points.length][0]-p[0], points[(i+1)%points.length][1]-p[1]));
    if (Number(value)>0 && sides[id-1]>0) sides.forEach((side,i) => { if (i!==id-1 && field(i+1).value==='') fireEvent.change(field(i+1), { target: { value: String(side * Number(value) / sides[id-1]) } }); });
    fireEvent.change(field(id), { target: { value: String(value) } });
  }

  test('longitudes explícitas compatibles conservan forma y ángulos del boceto', async () => {
    const onSave = vi.fn()
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={onSave} />)
    await draw(user, rectangle)
    await user.click(button('Cerrar polígono'))
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    measure(1, 800)
    expect(field(1)).toHaveValue(800)
    expect(field(2)).toHaveValue(400)
    expect(field(3)).toHaveValue(800)
    expect(field(4)).toHaveValue(400)
    expect(canvas().querySelector('.custom-piece-editor__vertex-label')).toHaveTextContent('V1 (90°)')
    expect(canvas().querySelector('polygon')).toHaveAttribute('data-provisional', 'false')
    await user.click(button('Agregar pieza al pedido'))
    onSave.mock.calls[0][0].vertices.forEach((point,i) => point.forEach((value,axis) => expect(value).toBeCloseTo([[0,0],[800,0],[800,400],[0,400]][i][axis],7)))
    expect(field(1)).toHaveValue(800)
  })

  test('editar otro lado conserva los demás campos y recalcula una geometría distinta', async () => {
    const user = setup()
    await draw(user, rectangle)
    await user.click(button('Cerrar polígono'))
    measure(1, 800)
    const preview = canvas().querySelector('polygon').getAttribute('points')
    measure(2, 600)
    expect(field(1)).toHaveValue(800)
    expect(field(2)).toHaveValue(600)
    const after = canvas().querySelector('polygon').getAttribute('points')
    expect(after).not.toBe(preview)
    expect(canvas().querySelector('.custom-piece-editor__vertex-label')).toHaveTextContent('°')
    expect(button('Agregar pieza al pedido')).toBeEnabled()
    expect(button('Agregar pieza al pedido')).toHaveAccessibleDescription('✓ Geometría validada y lista. Agrega la pieza y guarda el pedido para registrarla.')
  })

  test.each(['0','-1'])('medida %s inválida bloquea guardar y anuncia error accesible', async (value) => {
    const user = setup()
    await close(user)
    measure(1, value)
    await user.tab()
    expect(field(1)).toHaveAttribute('aria-invalid', 'true')
    expect(field(1)).toHaveAccessibleDescription('Número > 0')
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expect(canvas().querySelector('.custom-piece-editor__vertex-label')).not.toHaveTextContent('°')
  })

  test('borrar una longitud invalida el guardado hasta corregirla; reiniciar borra la escala', async () => {
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={vi.fn()} />)
    await close(user)
    measure(1, 850)
    expect(button('Agregar pieza al pedido')).toBeEnabled()
    await user.clear(field(2))
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    measure(2, 400)
    expect(button('Agregar pieza al pedido')).toBeEnabled()
    await user.click(button('Reiniciar'))
    expectInitial()
  })

  test.each([
    ['cóncavo', [[100,100],[500,100],[260,280],[500,460],[100,460]], /no es convexa/],
    ['autointersección', [[100,100],[400,500],[100,500],[400,100]], /intersecta consigo misma/],
    ['degenerado', [[100,100],[200,100],[300,100]], /área|colineal|degenerad/i],
  ])('contorno %s sigue rechazado después de cambiar escala', async (_name, points, message) => {
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={vi.fn()} />)
    await draw(user, points)
    await user.click(button('Cerrar polígono'))
    measure(1, 600)
    expect(screen.getByRole('alert', { name: 'Resultado de validación geométrica' })).toHaveTextContent(message)
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    measure(1, 900)
    expect(screen.getByRole('alert', { name: 'Resultado de validación geométrica' })).toHaveTextContent(message)
  })

  test('cierre y selección por teclado conservan foco y nombres accesibles', async () => {
    const user = setup()
    await draw(user)
    button('Cerrar polígono').focus()
    expect(button('Cerrar polígono')).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(field(1)).toHaveFocus()
    await user.tab()
    expect(selector(2)).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(field(2)).toHaveFocus()
    expect(selector(2)).toHaveAttribute('aria-pressed', 'true')
  })
})
