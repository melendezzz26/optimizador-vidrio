import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import NuevoPedido from '../NuevoPedido'

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }))

const materials = [
  { id_tipo_vidrio: 7, nombre: 'Material de prueba', estado: true, espesores_mm: [5.5, 6] },
  { id_tipo_vidrio: 8, nombre: 'Otro material', estado: true, espesores_mm: [4] },
]
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data })
const saveButton = () => screen.getByRole('button', { name: 'Guardar pedido' })
const orderPieces = () => [...document.querySelectorAll('.pieza')]
const pieceRow = (number) => {
  const heading = screen.getByText(`Pieza ${number}`)
  return heading.closest('.pieza')
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(materials)))
})
afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear() })

async function setup() {
  const user = userEvent.setup()
  render(<NuevoPedido token="test-token" />)
  await screen.findByText('No hay piezas agregadas')
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(fetch.mock.calls[0][0]).toMatch(/\/api\/inventory\/tipos-vidrio$/)
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer test-token')
  return user
}

async function addPiece(user) {
  await user.click(screen.getByRole('button', { name: 'Agregar pieza' }))
  return pieceRow(orderPieces().length)
}

async function selectMaterial(user, row, materialId, thickness) {
  const [material, espesor] = within(row).getAllByRole('combobox')
  await user.selectOptions(material, String(materialId))
  await user.selectOptions(espesor, String(thickness))
}

function setQuantity(row, value) {
  fireEvent.change(within(row).getAllByRole('spinbutton')[0], { target: { value: String(value) } })
}

function setRectangle(row, width, height) {
  const [, ancho, alto] = within(row).getAllByRole('spinbutton')
  fireEvent.change(ancho, { target: { value: String(width) } })
  fireEvent.change(alto, { target: { value: String(height) } })
}

async function addPolygon(user, row) {
  const [, , shape] = within(row).getAllByRole('combobox')
  await user.selectOptions(shape, 'POLIGONO_CONVEXO')
  const canvas = screen.getByRole('img', { name: /Lienzo del dibujo original/ })
  for (const [x, y] of [[100, 100], [400, 100], [400, 300], [100, 300]]) {
    await user.pointer({ target: canvas, keys: '[MouseLeft]', coords: { clientX: x, clientY: y } })
  }
  await user.click(screen.getByRole('button', { name: 'Cerrar polígono' }))
  for (const [index, value] of [300, 200, 300, 200].entries()) {
    fireEvent.change(screen.getByRole('spinbutton', { name: `Longitud del segmento S${index + 1} en milímetros` }), { target: { value: String(value) } })
  }
  expect(screen.getByText('Geometría convexa validada.')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Agregar pieza al pedido' }))
}

describe('HU-006: contrato multimaterial por pieza', () => {
  test('registra rectángulo, circunferencia y polígono con material, espesor y cantidad propios', async () => {
    const user = await setup()

    const polygon = await addPiece(user)
    await selectMaterial(user, polygon, 7, 5.5)
    setQuantity(polygon, 3)
    await addPolygon(user, polygon)

    const rectangle = await addPiece(user)
    await selectMaterial(user, rectangle, 8, 4)
    setQuantity(rectangle, 2)
    setRectangle(rectangle, 1000, 500)

    const circle = await addPiece(user)
    await selectMaterial(user, circle, 7, 6)
    setQuantity(circle, 1)
    await user.selectOptions(within(circle).getAllByRole('combobox')[2], 'CIRCUNFERENCIA')
    const [quantity, radius] = within(circle).getAllByRole('spinbutton')
    fireEvent.change(radius, { target: { value: '250' } })
    expect(quantity).toHaveValue(1)

    expect(saveButton()).toBeEnabled()
    expect(fetch).toHaveBeenCalledTimes(1)
    fetch.mockResolvedValueOnce(response({ id_pedido: 44, estado: 'PENDIENTE' }, 201))
    await user.click(saveButton())
    expect(await screen.findByText('Pedido registrado correctamente.')).toBeVisible()

    const [url, options] = fetch.mock.calls[1]
    expect(url).toMatch(/\/api\/orders\/$/)
    expect(options.method).toBe('POST')
    expect(options.headers.Authorization).toBe('Bearer test-token')
    const body = JSON.parse(options.body)
    expect(body).not.toHaveProperty('id_tipo_vidrio')
    expect(body).not.toHaveProperty('espesor_mm')
    expect(body.piezas).toEqual([
      {
        tipo_forma: 'POLIGONO_CONVEXO', id_tipo_vidrio: 7, espesor_mm: 5.5,
        cantidad: 3, vertices_mm: expect.any(Array),
      },
      {
        tipo_forma: 'RECTANGULO', id_tipo_vidrio: 8, espesor_mm: 4,
        cantidad: 2, width_mm: 1000, height_mm: 500,
      },
      {
        tipo_forma: 'CIRCUNFERENCIA', id_tipo_vidrio: 7, espesor_mm: 6,
        cantidad: 1, radius_mm: 250,
      },
    ])
    expect(screen.queryByText('Pieza 1')).not.toBeInTheDocument()
  })

  test('no permite guardar cantidad cero ni medidas no positivas', async () => {
    const user = await setup()
    const row = await addPiece(user)
    await selectMaterial(user, row, 7, 5.5)
    setRectangle(row, 100, 50)

    setQuantity(row, 0)
    expect(saveButton()).toBeDisabled()
    setQuantity(row, 1.5)
    expect(saveButton()).toBeDisabled()
    setQuantity(row, 1)
    expect(saveButton()).toBeEnabled()

    const [, width, height] = within(row).getAllByRole('spinbutton')
    for (const invalid of ['0', '-1']) {
      fireEvent.change(width, { target: { value: invalid } })
      expect(saveButton()).toBeDisabled()
      fireEvent.change(width, { target: { value: '100' } })
      fireEvent.change(height, { target: { value: invalid } })
      expect(saveButton()).toBeDisabled()
      fireEvent.change(height, { target: { value: '50' } })
    }
    expect(saveButton()).toBeEnabled()
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})

describe('HU-007 T04: persistencia de piezas', () => {
  test('el polígono requiere geometría válida antes de aceptar el dibujo', async () => {
    const user = await setup()
    const row = await addPiece(user)
    await selectMaterial(user, row, 7, 5.5)
    await user.selectOptions(within(row).getAllByRole('combobox')[2], 'POLIGONO_CONVEXO')

    const canvas = screen.getByRole('img', { name: /Lienzo del dibujo original/ })
    for (const [x, y] of [[100, 100], [500, 100], [260, 280], [500, 460], [100, 460]]) {
      await user.pointer({ target: canvas, keys: '[MouseLeft]', coords: { clientX: x, clientY: y } })
    }
    await user.click(screen.getByRole('button', { name: 'Cerrar polígono' }))
    for (let index = 1; index <= 5; index++) {
      fireEvent.change(screen.getByRole('spinbutton', { name: `Longitud del segmento S${index} en milímetros` }), {
        target: { value: ['400', '300', '300', '400', '360'][index - 1] },
      })
    }
    expect(screen.getByRole('alert', { name: 'Resultado de validación geométrica' })).toHaveTextContent('La figura resultante no es convexa.')
    expect(screen.getByRole('button', { name: 'Agregar pieza al pedido' })).toBeDisabled()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  test('envía un único POST mientras guarda y limpia solo al confirmar éxito', async () => {
    const user = await setup()
    const row = await addPiece(user)
    await selectMaterial(user, row, 8, 4)
    setQuantity(row, 2)
    setRectangle(row, 1000, 500)

    let resolvePost
    fetch.mockImplementationOnce(() => new Promise((resolve) => { resolvePost = resolve }))
    await user.click(saveButton())
    await user.click(screen.getByRole('button', { name: /Guardando/ }))

    expect(fetch).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('button', { name: /Guardando/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()

    await act(async () => resolvePost(response({ id_pedido: 42, estado: 'PENDIENTE' }, 201)))
    expect(await screen.findByText('Pedido registrado correctamente.')).toBeVisible()
    expect(screen.queryByText('Pieza 1')).not.toBeInTheDocument()
    expect(saveButton()).toBeDisabled()
  })

  test.each([401, 403, 422, 500, 'network'])('ante error %s conserva el borrador y permite reintentar', async (failure) => {
    const user = await setup()
    const row = await addPiece(user)
    await selectMaterial(user, row, 7, 5.5)
    setRectangle(row, 1000, 500)
    const payload = {
      detail: failure === 422 ? [{ loc: ['body', 'piezas', 0], msg: 'field required' }] : 'No se pudo guardar',
    }
    if (failure === 'network') fetch.mockRejectedValueOnce(new TypeError('offline'))
    else fetch.mockResolvedValueOnce(response(payload, failure))

    await user.click(saveButton())
    const alert = await screen.findByRole('alert')
    expect(alert).toBeVisible()
    expect(alert).not.toHaveTextContent('field required')
    expect(screen.getByText('Pieza 1')).toBeVisible()
    expect(saveButton()).toBeEnabled()

    const firstBody = fetch.mock.calls[1][1].body
    fetch.mockResolvedValueOnce(response({ id_pedido: 43, estado: 'PENDIENTE' }, 201))
    await user.click(saveButton())
    expect(await screen.findByText('Pedido registrado correctamente.')).toBeVisible()
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual(JSON.parse(firstBody))
  })

  test('muestra el error de catálogo sin inventar controles de reintento', async () => {
    fetch.mockRejectedValueOnce(new TypeError('offline'))
    render(<NuevoPedido token="test-token" />)

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo completar la operación')
    expect(saveButton()).toBeDisabled()
    expect(screen.queryByRole('button', { name: /Reintentar catálogo/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Material de prueba' })).not.toBeInTheDocument()
  })
})
