import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import NuevoPedido from '../../../pages/NuevoPedido'

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }))

const materials = [
  { id_tipo_vidrio: 7, nombre: 'Material de prueba', estado: true, espesores_mm: [5.5, 6] },
  { id_tipo_vidrio: 9, nombre: 'Inactivo', estado: false, espesores_mm: [6] },
]
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data })
const saveButton = () => screen.getByRole('button', { name: 'Guardar pedido' })
const addButton = () => screen.getByRole('button', { name: 'Agregar pieza al pedido' })

beforeEach(() => {
  sessionStorage.setItem('optimizador.auth', JSON.stringify({ access_token: 'test-token', usuario: { id_usuario: 3 } }))
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(materials)))
})
afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear() })

async function setup() {
  const user = userEvent.setup()
  render(<NuevoPedido />)
  await screen.findByRole('option', { name: 'Material de prueba' })
  return user
}

async function selectHeader(user) {
  await user.selectOptions(screen.getByLabelText('Tipo de vidrio'), '7')
  await user.selectOptions(screen.getByLabelText('Espesor'), '5.5')
}

async function validPolygon(user) {
  const canvas = screen.getByRole('img', { name: /Lienzo del dibujo original/ })
  for (const [x, y] of [[100, 100], [400, 100], [400, 300], [100, 300]]) {
    await user.pointer({ target: canvas, keys: '[MouseLeft]', coords: { clientX: x, clientY: y } })
  }
  await user.click(screen.getByRole('button', { name: 'Cerrar polígono' }))
  for (const [index, value] of [300, 200, 300, 200].entries()) {
    fireEvent.change(screen.getByRole('spinbutton', { name: `Longitud del segmento S${index + 1} en milímetros` }), { target: { value: String(value) } })
  }
  expect(screen.getByText('Geometría convexa validada.')).toBeVisible()
}

describe('HU-007 T04: pedido y piezas', () => {
  test('catálogo real y geometría VALID requeridos; agregar solo local y reiniciar lienzo', async () => {
    const user = await setup()
    expect(screen.queryByRole('option', { name: 'Inactivo' })).not.toBeInTheDocument()
    expect(addButton()).toBeDisabled()
    await validPolygon(user)
    expect(addButton()).toBeDisabled()
    await selectHeader(user)
    expect(addButton()).toBeEnabled()
    await user.click(addButton())
    expect(screen.getByText('Pieza 1')).toBeVisible()
    expect(screen.getByText('0 vértices')).toBeVisible()
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(saveButton()).toBeEnabled()
    await user.click(screen.getByRole('button', { name: 'Eliminar pieza 1' }))
    expect(saveButton()).toBeDisabled()
  })

  test('múltiples piezas, un POST, bloqueo mientras guarda y éxito con id_pedido', async () => {
    const user = await setup()
    await selectHeader(user)
    for (let i = 0; i < 2; i++) { await validPolygon(user); await user.click(addButton()) }
    let resolve
    fetch.mockImplementationOnce(() => new Promise((done) => { resolve = done }))
    const save = saveButton()
    fireEvent.click(save)
    fireEvent.click(save)
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('button', { name: 'Guardando pedido…' })).toBeDisabled()
    expect(screen.getByLabelText('Tipo de vidrio')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Eliminar pieza 1' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
    const [url, options] = fetch.mock.calls[1]
    expect(url).toMatch(/\/api\/orders$/)
    expect(options.headers.Authorization).toBe('Bearer test-token')
    const payload = JSON.parse(options.body)
    expect(payload.id_tipo_vidrio).toBe(7)
    expect(payload.espesor_mm).toBe(5.5)
    expect(payload.piezas).toHaveLength(2)
    expect(Object.keys(payload.piezas[0]).sort()).toEqual(['cantidad', 'tipo_forma', 'vertices_mm'])
    await act(async () => resolve(response({ id_pedido: 42, estado: 'PENDIENTE' }, 201)))
    expect(screen.getByText(/ID del pedido: 42/)).toBeVisible()
    expect(screen.queryByText('Pieza 1')).not.toBeInTheDocument()
    expect(saveButton()).toBeDisabled()
  })

  test.each([401, 403, 422, 500, 'network'])('fallo %s conserva piezas y permite reintentar', async (status) => {
    const user = await setup()
    await selectHeader(user)
    await validPolygon(user)
    await user.click(addButton())
    if (status === 'network') fetch.mockRejectedValueOnce(new TypeError('offline'))
    else fetch.mockResolvedValueOnce(response({ detail: 'No se pudo guardar' }, status))
    await user.click(saveButton())
    expect(await screen.findByRole('alert')).toHaveTextContent('Las piezas se conservan')
    expect(screen.getByText('Pieza 1')).toBeVisible()
    expect(saveButton()).toBeEnabled()
    fetch.mockResolvedValueOnce(response({ id_pedido: 43 }, 201))
    await user.click(saveButton())
    await screen.findByText(/ID del pedido: 43/)
    expect(fetch.mock.calls[1][1].body).toBe(fetch.mock.calls[2][1].body)
  })

  test('error de catálogo permite reintentar sin usar valores estáticos', async () => {
    fetch.mockRejectedValueOnce(new TypeError('offline'))
    const user = userEvent.setup()
    render(<NuevoPedido />)
    await screen.findByRole('alert')
    expect(saveButton()).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Reintentar catálogo' }))
    await screen.findByRole('option', { name: 'Material de prueba' })
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  })
})
