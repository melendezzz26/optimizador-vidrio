// Regression suite adapted to explicit independent lengths and a sketch initial guess.
import { render, screen, fireEvent, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import CustomPieceEditor from '../CustomPieceEditor'

const pentagon = [[200, 50], [500, 50], [600, 250], [350, 450], [100, 250]]
const canvas = () => screen.getByRole('img', { name: /Lienzo del dibujo original/ })
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
  expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('Pendiente de completar dimensiones.')
}

describe('HU-007 T01 — dibujo y controles (caja negra)', () => {
  test('T01-C01: editor inicial visible, accesible y sin dimensiones', () => {
    setup()
    expect(screen.getByRole('region', { name: 'Pieza personalizada' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Dibujo original' })).toBeVisible()
    expect(screen.getByRole('group', { name: 'Herramientas de dibujo' })).toBeVisible()
    expect(canvas()).toHaveAccessibleDescription(/Faltan 3 vértices/)
    expect(screen.getByText(/Las piezas agregadas se registran al guardar/)).toBeVisible()
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

describe('TA-036: regresiones vigentes del editor', () => {
  const measure = (id, value) => {
    // Enter every still-empty side explicitly; the production editor never fills other fields.
    const points = canvas().querySelector('polygon').getAttribute('points').split(' ').map(p => p.split(',').map(Number));
    const sides = points.map((p,i) => Math.hypot(points[(i+1)%points.length][0]-p[0], points[(i+1)%points.length][1]-p[1]));
    if (Number(value)>0 && sides[id-1]>0) sides.forEach((side,i) => { if (i!==id-1 && field(i+1).value==='') fireEvent.change(field(i+1), { target: { value: String(side * Number(value) / sides[id-1]) } }); });
    fireEvent.change(field(id), { target: { value: String(value) } });
  }

  function expectSynchronized(id, previewName) {
    expect(selector(id)).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getAllByRole('button', { pressed: true })).toEqual([selector(id)])
    const preview = screen.getByRole('img', { name: previewName })
    // SVG primitives are aria-hidden; visible selection is checked in both renders.
    for (const view of [canvas(), preview]) {
      expect(view.querySelectorAll('line[data-active="true"]')).toHaveLength(1)
      expect(view.querySelectorAll('line')[id - 1]).toHaveAttribute('data-active', 'true')
      expect(view.querySelectorAll('text[data-active="true"]')).toHaveLength(1)
      expect(view.querySelector('text[data-active="true"]')).toHaveTextContent(`S${id}`)
    }
  }

  test('cierre identifica todos los campos requeridos sin escala física ni geometría guardable', async () => {
    const user = setup()
    await close(user)
    for (let id = 1; id <= 5; id++) {
      expect(field(id)).toHaveValue(null)
      expect(field(id)).toBeRequired()
      expect(field(id)).toHaveAttribute('step', 'any')
    }
    expect(screen.getByText('0 de 5 medidas ingresadas')).toBeVisible()
    expect(screen.getByText(/Completa todos los lados/)).toBeVisible()
    expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('Pendiente de completar dimensiones.')
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expectSynchronized(1, 'Vista dimensional provisional. Segmento S1 seleccionado.')
  })

  test('selección y hover conservan arista y etiqueta sincronizadas en ambos SVG sin alterar medidas', async () => {
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
    expect(screen.getByRole('region', { name: 'Ángulos interiores' })).toHaveTextContent('V1: 90°')
    expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('Geometría convexa validada.')
    await user.click(button('Agregar pieza al pedido'))
    const vertices = onSave.mock.calls[0][0].vertices
    const expected = [[0, 0], [0.001, 0], [0.001, 0.0005], [0, 0.0005]]
    vertices.forEach((point, i) => point.forEach((value, axis) => expect(value).toBeCloseTo(expected[i][axis], 12)))
  })

  test('deshacer una figura dimensionada invalida el resultado y recerrar crea campos vacíos', async () => {
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={vi.fn()} />)
    await close(user)
    measure(1, 850)
    await user.click(selector(5))
    expect(button('Agregar pieza al pedido')).toBeEnabled()
    await user.click(button('Deshacer último vértice'))
    expect(screen.queryByRole('img', { name: /Vista dimensional/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Ángulos interiores' })).not.toBeInTheDocument()
    expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('Pendiente de completar dimensiones.')
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    await user.click(button('Cerrar polígono'))
    expect(screen.getAllByRole('spinbutton')).toHaveLength(4)
    screen.getAllByRole('spinbutton').forEach(input => expect(input).toHaveValue(null))
    expectSynchronized(1, 'Vista dimensional provisional. Segmento S1 seleccionado.')
  })

  test('reiniciar después de medir elimina escala y selección antes del siguiente dibujo', async () => {
    const user = setup()
    await close(user)
    measure(1, 850)
    await user.click(selector(5))
    await user.click(button('Reiniciar dibujo'))
    expectInitial()
    await close(user)
    screen.getAllByRole('spinbutton').forEach(input => expect(input).toHaveValue(null))
    expectSynchronized(1, 'Vista dimensional provisional. Segmento S1 seleccionado.')
    expect(screen.queryByRole('region', { name: 'Ángulos interiores' })).not.toBeInTheDocument()
  })

  test('borrar todas las medidas retira escala, ángulos y resultado válido anterior', async () => {
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={vi.fn()} />)
    await close(user)
    measure(1, 850)
    for (let id = 1; id <= 5; id++) await user.clear(field(id))
    expect(screen.getByText('0 de 5 medidas ingresadas')).toBeVisible()
    expect(screen.getByText(/Completa todos los lados/)).toBeVisible()
    expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('Pendiente de completar dimensiones.')
    expect(screen.queryByRole('region', { name: 'Ángulos interiores' })).not.toBeInTheDocument()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
  })

  test('geometría completa no autoriza guardar sin material de pedido válido', async () => {
    const onSave = vi.fn()
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={onSave} headerReady={false} />)
    await close(user)
    measure(1, 850)
    expect(screen.getByText('Geometría convexa validada.')).toBeVisible()
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

  test('selección por foco directo se refleja en líneas y etiquetas de ambas vistas', async () => {
    const user = setup()
    await close(user)
    measure(1, 850)
    await user.click(field(4))
    expectSynchronized(4, 'Vista dimensional completa. Segmento S4 seleccionado.')
    expect(within(screen.getByRole('region', { name: 'Dimensiones por segmento' })).getAllByRole('spinbutton')).toHaveLength(5)
  })

  test('invalidar y corregir una dimensión retira y recalcula la validación sin geometría obsoleta', async () => {
    const user = userEvent.setup()
    render(<CustomPieceEditor initialState={{ construction: { mode: 'guided', angle: '90' } }} onGuardarVertices={vi.fn()} />)
    await close(user)
    measure(1, 850)
    expect(button('Agregar pieza al pedido')).toBeEnabled()
    measure(1, 0)
    expect(field(1)).toHaveAttribute('aria-invalid', 'true')
    expect(screen.queryByText('Geometría convexa validada.')).not.toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /Vista dimensional/ })).not.toBeInTheDocument()
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    measure(1, 900)
    expect(screen.getByText('Geometría convexa validada.')).toBeVisible()
    expect(field(1)).toHaveValue(900)
    expect(button('Agregar pieza al pedido')).toBeEnabled()
    await user.clear(field(1))
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('Pendiente de completar dimensiones.')
    measure(1, 850)
    expect(screen.getByText('Geometría convexa validada.')).toBeVisible()
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
    expect(screen.getByRole('region', { name: 'Ángulos interiores' })).toHaveTextContent('V1: 90°')
    expect(canvas().querySelector('polygon')).toHaveAttribute('points', rectangle.map(p => p.join(',')).join(' '))
    await user.click(button('Agregar pieza al pedido'))
    onSave.mock.calls[0][0].vertices.forEach((point,i) => point.forEach((value,axis) => expect(value).toBeCloseTo([[0,0],[800,0],[800,400],[0,400]][i][axis],7)))
    expectInitial()
  })

  test('editar otro lado conserva los demás campos y recalcula una geometría distinta', async () => {
    const user = setup()
    await draw(user, rectangle)
    await user.click(button('Cerrar polígono'))
    measure(1, 800)
    const preview = screen.getByRole('img', { name: /Vista dimensional completa/ }).querySelector('polygon').getAttribute('points')
    measure(2, 600)
    expect(field(1)).toHaveValue(800)
    expect(field(2)).toHaveValue(600)
    const after = screen.getByRole('img', { name: /Vista dimensional completa/ }).querySelector('polygon').getAttribute('points')
    expect(after).not.toBe(preview)
    expect(screen.getByRole('region', { name: 'Ángulos interiores' })).toHaveTextContent('Calculado')
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expect(button('Agregar pieza al pedido')).toHaveAccessibleDescription('Geometría convexa validada. Agrega la pieza y guarda el pedido para registrarla.')
  })

  test.each(['0','-1'])('medida %s inválida bloquea guardar y anuncia error accesible', async (value) => {
    const user = setup()
    await close(user)
    measure(1, value)
    await user.tab()
    expect(field(1)).toHaveAttribute('aria-invalid', 'true')
    expect(field(1)).toHaveAccessibleDescription('Usa un número finito mayor que 0.')
    expect(button('Agregar pieza al pedido')).toBeDisabled()
    expect(screen.queryByRole('region', { name: 'Ángulos interiores' })).not.toBeInTheDocument()
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
    await user.click(button('Reiniciar dibujo'))
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
  })
})
