import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import FormularioPedido from '../FormularioPedido'

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }))

const materials = [
  { id_tipo_vidrio: 7, nombre: 'Material de prueba', estado: true, espesores_mm: [5.5, 6] },
  { id_tipo_vidrio: 8, nombre: 'Otro material', estado: true, espesores_mm: [4] },
]
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data })
const saveButton = () => screen.getByRole('button', { name: 'Guardar pedido' })
const pieceHeadings = () => screen.queryAllByText(/^Pieza \d+$/, { selector: 'strong' })
const orderPieces = () => pieceHeadings().map((heading) => heading.closest('.orders-piece'))
const pieceRow = (number) => {
  const heading = screen.getByText(`Pieza ${number}`, { selector: 'strong' })
  return heading.closest('.orders-piece')
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(materials)))
})
afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear() })

async function setup() {
  const user = userEvent.setup()
  render(<FormularioPedido token="test-token" standalone />)
  await screen.findByText('Falta seleccionar cliente')
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(fetch.mock.calls[0][0]).toMatch(/\/api\/inventory\/tipos-vidrio$/)
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer test-token')
  fetch.mockResolvedValueOnce(response([{ id_cliente: 41, nombre_razon_social: 'Cliente prueba', estado: true }]))
  fireEvent.change(screen.getByLabelText('Nombre del cliente'), { target: { value: 'prueba' } })
  fireEvent.click(screen.getByRole('button', { name: 'Buscar', exact: true }))
  fireEvent.click(await screen.findByRole('button', { name: 'Seleccionar Cliente prueba' }))
  return user
}

function initialPiece() { return pieceRow(1) }

async function addMaterial(user) {
  await user.click(screen.getByRole('button', { name: 'Agregar otro vidrio' }))
  return pieceRow(orderPieces().length)
}

async function selectMaterial(user, row, materialId, thickness) {
  const group = within(row.closest('.orders-material-group'))
  const material = group.getByLabelText('Tipo de vidrio')
  const espesor = group.getByLabelText('Espesor del vidrio (mm)')
  await user.selectOptions(material, String(materialId))
  await user.selectOptions(espesor, String(thickness))
}

function setQuantity(row, value) {
  fireEvent.change(within(row).getByLabelText('Cantidad'), { target: { value: String(value) } })
}

function setRectangle(row, width, height) {
  const ancho = within(row).getByLabelText('Ancho (mm)')
  const alto = within(row).getByLabelText('Alto (mm)')
  fireEvent.change(ancho, { target: { value: String(width) } })
  fireEvent.change(alto, { target: { value: String(height) } })
}

async function addPolygon(user, row) {
  const shape = within(row).getByLabelText('Forma')
  await user.selectOptions(shape, 'POLIGONO_CONVEXO')
  const canvas = screen.getByRole('img', { name: /Lienzo del dibujo original/ })
  for (const [x, y] of [[100, 100], [400, 100], [400, 300], [100, 300]]) {
    await user.pointer({ target: canvas, keys: '[MouseLeft]', coords: { clientX: x, clientY: y } })
  }
  await user.click(screen.getByRole('button', { name: 'Cerrar polígono' }))
  for (const [index, value] of [300, 200, 300, 200].entries()) {
    fireEvent.change(screen.getByRole('spinbutton', { name: `Longitud del segmento S${index + 1} en milímetros` }), { target: { value: String(value) } })
  }
  expect(screen.getByText('✓ Geometría validada y lista.')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Agregar pieza al pedido' }))
}

describe('FIX-003/005: composición y accesibilidad de Orders', () => {
  test('conserva el formulario actual y no muestra navegación lateral inerte ni lista de pedidos', async () => {
    const user = await setup()

    expect(screen.getByRole('heading', { name: 'Nuevo pedido' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Agregar pieza' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Inicio' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Gestión de inventario' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /pedidos registrados/i })).not.toBeInTheDocument()
    expect(screen.queryByText('Falta seleccionar cliente')).not.toBeInTheDocument()
    await selectMaterial(user, initialPiece(), 7, 5.5)
    expect(screen.getByRole('button', { name: 'Agregar pieza' })).toBeEnabled()
    expect(screen.getByText('Pieza 1')).toBeVisible()
  })

  test('asocia labels de material, espesor, forma, cantidad y medidas a sus controles', async () => {
    await setup()
    const row = initialPiece()

    expect(within(row.closest('.orders-material-group')).getByLabelText('Tipo de vidrio')).toBeVisible()
    expect(within(row.closest('.orders-material-group')).getByLabelText('Espesor del vidrio (mm)')).toBeDisabled()
    expect(within(row).getByLabelText('Forma')).toHaveValue('RECTANGULO')
    expect(within(row).getByLabelText('Cantidad')).toHaveValue(1)
    expect(within(row).getByLabelText('Ancho (mm)')).toBeVisible()
    expect(within(row).getByLabelText('Alto (mm)')).toBeVisible()
  })

  test('mantiene identidad, keys e IDs de controles únicos al agregar piezas en el mismo milisegundo', async () => {
    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(123456789)
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    try {
      const user = await setup()
      const firstPiece = initialPiece()
      await selectMaterial(user, firstPiece, 7, 5.5)
      await user.click(screen.getByRole('button', { name: 'Agregar pieza' }))
      const secondPiece = pieceRow(2)
      await user.selectOptions(within(secondPiece).getByLabelText('Forma'), 'CIRCUNFERENCIA')

      expect(orderPieces()).toHaveLength(2)
      const firstQuantity = within(firstPiece).getByLabelText('Cantidad')
      const secondQuantity = within(secondPiece).getByLabelText('Cantidad')
      fireEvent.change(firstQuantity, { target: { value: '3' } })
      expect(firstQuantity).toHaveValue(3)
      expect(secondQuantity).toHaveValue(1)

      const expectedLabels = [
        [firstPiece, ['Forma', 'Cantidad', 'Ancho (mm)', 'Alto (mm)']],
        [secondPiece, ['Forma', 'Cantidad', 'Radio (mm)']],
      ]
      for (const [row, labels] of expectedLabels) {
        for (const labelText of labels) {
          const control = within(row).getByLabelText(labelText)
          const label = within(row).getByText(labelText, { selector: 'label' })
          expect(label).toHaveAttribute('for', control.id)
          expect(control.id).not.toBe('')
        }
      }

      const ids = [...document.querySelectorAll('[id]')].map((element) => element.id)
      expect(new Set(ids).size).toBe(ids.length)
      expect(consoleErrorSpy.mock.calls.flat().join(' ')).not.toMatch(/same key/i)
      expect(fetch).toHaveBeenCalledTimes(2)
    } finally {
      nowSpy.mockRestore()
      consoleErrorSpy.mockRestore()
    }
  })

  test('el editor poligonal se identifica como diálogo, soporta Escape y devuelve el foco', async () => {
    const user = await setup()
    const row = initialPiece()
    await selectMaterial(user, row, 7, 5.5)
    const shapeSelect = within(row).getByLabelText('Forma')

    await user.selectOptions(shapeSelect, 'POLIGONO_CONVEXO')
    const dialog = screen.getByRole('dialog', { name: 'Dibujar Polígono Convexo' })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByRole('button', { name: 'Cerrar editor de polígono' })).toHaveFocus()

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog', { name: 'Dibujar Polígono Convexo' })).not.toBeInTheDocument()
    expect(shapeSelect).toHaveFocus()
  })
})

describe('HU-006: contrato de piezas agrupadas por material y espesor', () => {
  test('registra rectángulo, circunferencia y polígono con material, espesor y cantidad propios', async () => {
    const user = await setup()

    const polygon = initialPiece()
    await selectMaterial(user, polygon, 7, 5.5)
    setQuantity(polygon, 3)
    await addPolygon(user, polygon)

    const rectangle = await addMaterial(user)
    await selectMaterial(user, rectangle, 8, 4)
    setQuantity(rectangle, 2)
    setRectangle(rectangle, 1000, 500)

    const circle = await addMaterial(user)
    await selectMaterial(user, circle, 7, 6)
    setQuantity(circle, 1)
    await user.selectOptions(within(circle).getByLabelText('Forma'), 'CIRCUNFERENCIA')
    const quantity = within(circle).getByLabelText('Cantidad')
    const radius = within(circle).getByLabelText('Radio (mm)')
    fireEvent.change(radius, { target: { value: '250' } })
    expect(quantity).toHaveValue(1)

    expect(saveButton()).toBeEnabled()
    expect(fetch).toHaveBeenCalledTimes(2)
    fetch.mockResolvedValueOnce(response({ id_pedido: 44, estado: 'PENDIENTE' }, 201))
    await user.click(saveButton())
    expect(await screen.findByText(/Pedido registrado correctamente. ID del pedido:/)).toBeVisible()

    const [url, options] = fetch.mock.calls[2]
    expect(url).toMatch(/\/api\/orders$/)
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
    const row = initialPiece()
    await selectMaterial(user, row, 7, 5.5)
    setRectangle(row, 100, 50)

    setQuantity(row, 0)
    expect(saveButton()).toBeDisabled()
    setQuantity(row, 1.5)
    expect(saveButton()).toBeDisabled()
    setQuantity(row, 1)
    expect(saveButton()).toBeEnabled()

    const width = within(row).getByLabelText('Ancho (mm)')
    const height = within(row).getByLabelText('Alto (mm)')
    for (const invalid of ['0', '-1']) {
      fireEvent.change(width, { target: { value: invalid } })
      expect(saveButton()).toBeDisabled()
      fireEvent.change(width, { target: { value: '100' } })
      fireEvent.change(height, { target: { value: invalid } })
      expect(saveButton()).toBeDisabled()
      fireEvent.change(height, { target: { value: '50' } })
    }
    expect(saveButton()).toBeEnabled()
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})

describe('HU-007 T04: persistencia de piezas', () => {
  test('el polígono requiere geometría válida antes de aceptar el dibujo', async () => {
    const user = await setup()
    const row = initialPiece()
    await selectMaterial(user, row, 7, 5.5)
    await user.selectOptions(within(row).getByLabelText('Forma'), 'POLIGONO_CONVEXO')

    const canvas = screen.getByRole('img', { name: /Lienzo del dibujo original/ })
    for (const [x, y] of [[100, 100], [500, 100], [260, 280], [500, 460], [100, 460]]) {
      await user.pointer({ target: canvas, keys: '[MouseLeft]', coords: { clientX: x, clientY: y } })
    }
    await user.click(screen.getByRole('button', { name: 'Cerrar polígono' }))
    // This case validates the drawn concave contour, not a new cyclic construction.
    await user.selectOptions(screen.getByRole('combobox', { name: 'Comportamiento de la figura' }), 'guided')
    for (let index = 1; index <= 5; index++) {
      fireEvent.change(screen.getByRole('spinbutton', { name: `Longitud del segmento S${index} en milímetros` }), {
        target: { value: ['400', '300', '300', '400', '360'][index - 1] },
      })
    }
    expect(screen.getByRole('alert', { name: 'Resultado de validación geométrica' })).toHaveTextContent('La figura resultante no es convexa.')
    expect(screen.getByRole('button', { name: 'Agregar pieza al pedido' })).toBeDisabled()
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  test('envía un único POST mientras guarda y limpia solo al confirmar éxito', async () => {
    const user = await setup()
    const row = initialPiece()
    await selectMaterial(user, row, 8, 4)
    setQuantity(row, 2)
    setRectangle(row, 1000, 500)

    let resolvePost
    fetch.mockImplementationOnce(() => new Promise((resolve) => { resolvePost = resolve }))
    await user.click(saveButton())
    await user.click(screen.getByRole('button', { name: /Guardando/ }))

    expect(fetch).toHaveBeenCalledTimes(3)
    expect(screen.getByRole('button', { name: /Guardando/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()

    await act(async () => resolvePost(response({ id_pedido: 42, estado: 'PENDIENTE' }, 201)))
    expect(await screen.findByText(/Pedido registrado correctamente. ID del pedido:/)).toBeVisible()
    expect(screen.queryByText('Pieza 1')).not.toBeInTheDocument()
    expect(saveButton()).toBeDisabled()
  })

  test.each([401, 403, 422, 500, 'network'])('ante error %s conserva el borrador y permite reintentar', async (failure) => {
    const user = await setup()
    const row = initialPiece()
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

    const firstBody = fetch.mock.calls[2][1].body
    fetch.mockResolvedValueOnce(response({ id_pedido: 43, estado: 'PENDIENTE' }, 201))
    await user.click(saveButton())
    expect(await screen.findByText(/Pedido registrado correctamente. ID del pedido:/)).toBeVisible()
    expect(JSON.parse(fetch.mock.calls[3][1].body)).toEqual(JSON.parse(firstBody))
  })

  test('muestra el error de catálogo y permite reintentar sin inventar materiales', async () => {
    fetch.mockRejectedValueOnce(new TypeError('offline'))
    render(<FormularioPedido token="test-token" standalone />)

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo completar la operación')
    expect(saveButton()).toBeDisabled()
    expect(screen.getByRole('button', { name: /Reintentar catálogo/i })).toBeEnabled()
    expect(screen.queryByRole('option', { name: 'Material de prueba' })).not.toBeInTheDocument()
  })
})
