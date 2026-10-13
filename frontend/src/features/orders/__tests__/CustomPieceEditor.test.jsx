import { render, screen, fireEvent } from '@testing-library/react'
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

describe('TA-036: vértices canónicos, escala y ángulos', () => {
  const rectangle = [[100, 100], [500, 100], [500, 300], [100, 300]]
  const measure = (index, value) => fireEvent.change(field(index), { target: { value: String(value) } })

  test('una longitud fija escala y deriva todos los lados y ángulos sin alterar el contorno', async () => {
    const onSave = vi.fn()
    const user = userEvent.setup()
    render(<CustomPieceEditor onGuardarVertices={onSave} />)
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
    expect(onSave.mock.calls[0][0].vertices).toEqual([[0,0],[800,0],[800,400],[0,400]])
    expectInitial()
  })

  test('editar otro lado reescala proporcionalmente sin cambiar ángulos ni proporción visual', async () => {
    const user = setup()
    await draw(user, rectangle)
    await user.click(button('Cerrar polígono'))
    measure(1, 800)
    const preview = screen.getByRole('img', { name: /Vista dimensional completa/ }).querySelector('polygon').getAttribute('points')
    measure(2, 600)
    expect(field(1)).toHaveValue(1200)
    expect(field(2)).toHaveValue(600)
    const after = screen.getByRole('img', { name: /Vista dimensional completa/ }).querySelector('polygon').getAttribute('points')
    after.split(/[ ,]/).map(Number).forEach((value,i) => expect(value).toBeCloseTo(preview.split(/[ ,]/).map(Number)[i],8))
    expect(screen.getByRole('region', { name: 'Ángulos interiores' })).toHaveTextContent('V4: 90°')
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
    render(<CustomPieceEditor onGuardarVertices={vi.fn()} />)
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
    render(<CustomPieceEditor onGuardarVertices={vi.fn()} />)
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
    await user.keyboard('{Enter}')
    expect(field(1)).toHaveFocus()
    await user.tab()
    expect(selector(2)).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(field(2)).toHaveFocus()
    expect(selector(2)).toHaveAttribute('aria-pressed', 'true')
  })
})
