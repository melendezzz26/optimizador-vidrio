import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { InventoryPage } from '../InventoryPage'
import { withPermissions } from '../../authentication/__tests__/permissionFixtures'

const catalogo = [
  {
    id_tipo_vidrio: 1,
    nombre: 'Incoloro',
    estado: true,
    espesores_mm: [6],
  },
]

const planchas = [
  {
    id_plancha: 4,
    id_tipo_vidrio: 1,
    espesor_mm: 6,
    ancho_mm: 1000,
    alto_mm: 500,
    cantidad: 2,
    estado: true,
    fecha_registro: '2026-10-08T12:00:00',
  },
]

const response = (data, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => data,
})

beforeEach(() => {
  sessionStorage.setItem(
    'optimizador.auth',
    JSON.stringify({
      access_token: 'test-token',
      usuario: {
        id_usuario: 4,
        username: 'A00000001',
        nombre: 'Cuenta Prueba Almacen',
        rol: 'Almacenero',
      },
    }),
  )

  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  vi.unstubAllGlobals()
  sessionStorage.clear()
})

async function renderInventory(onSessionExpired = vi.fn(), retazoRows = [], planchaRows = planchas) {
  fetch
    .mockResolvedValueOnce(response(catalogo))
    .mockResolvedValueOnce(response(planchaRows))
    .mockResolvedValueOnce(response(retazoRows))

  const user = userEvent.setup()

  render(
    <InventoryPage
      user={withPermissions({
        id_usuario: 4,
        username: 'A00000001',
        nombre: 'Cuenta Prueba Almacen',
        rol: 'Almacenero',
      })}
      toolbar={<div>Toolbar</div>}
      onSessionExpired={onSessionExpired}
    />,
  )

  await screen.findByText('Mostrando 1 de 1 planchas')

  return { user, onSessionExpired }
}

describe('TA-011 — errores HTTP de Inventario', () => {
  test('403 al editar conserva sesión y borrador sin refrescar ni cambiar el inventario', async () => {
    const { user, onSessionExpired } = await renderInventory()
    await user.click(screen.getByRole('button', { name: 'Editar' }))
    const cantidad = screen.getByRole('spinbutton', { name: /Cantidad/i })
    await user.clear(cantidad)
    await user.type(cantidad, '3')
    fetch.mockResolvedValueOnce(response({ detail: 'No tienes el permiso: GESTIONAR_PLANCHAS' }, 403))
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No tienes el permiso: GESTIONAR_PLANCHAS')
    expect(cantidad).toHaveValue(3)
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeEnabled()
    expect(onSessionExpired).not.toHaveBeenCalled()
    expect(sessionStorage.getItem('optimizador.auth')).not.toBeNull()
    expect(fetch).toHaveBeenCalledTimes(4)
    expect(fetch.mock.calls[3][1].method).toBe('PATCH')
    expect(fetch.mock.calls[3][1].headers.Authorization).toBe('Bearer test-token')
    expect(JSON.parse(fetch.mock.calls[3][1].body)).toEqual({ cantidad: 3 })
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.getByRole('cell', { name: '2' })).toBeVisible()
    expect(screen.getByRole('cell', { name: 'Activo' })).toBeVisible()
  })

  test('cancelar la revisión de baja parcial no envía POST y restaura el foco sin cambiar saldo', async () => {
    const { user } = await renderInventory()
    const trigger = screen.getByRole('button', { name: 'Dar de baja plancha #4' })
    await user.click(trigger)
    await user.type(screen.getByLabelText(/Motivo/), 'Una unidad dañada')
    await user.click(screen.getByRole('button', { name: 'Revisar baja' }))
    const dialog = screen.getByRole('dialog', { name: 'Confirmar baja manual' })
    expect(dialog).toHaveTextContent('Cantidad restante1')
    await user.click(within(dialog).getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(screen.getByRole('cell', { name: '2' })).toBeVisible()
    expect(screen.getByRole('cell', { name: 'Activo' })).toBeVisible()
    expect(trigger).toHaveFocus()
  })

  test('editar cantidad usa PATCH y refresca el saldo visible manteniendo historial y baja', async () => {
    const { user } = await renderInventory()
    await user.click(screen.getByRole('button', { name: 'Editar' }))
    const cantidad = screen.getByRole('spinbutton', { name: /Cantidad/i })
    await user.clear(cantidad)
    await user.type(cantidad, '5')
    fetch.mockResolvedValueOnce(response({ ...planchas[0], cantidad: 5 }))
      .mockResolvedValueOnce(response([{ ...planchas[0], cantidad: 5 }]))
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    expect(await screen.findByText('Plancha actualizada correctamente.')).toBeVisible()
    expect(screen.getByRole('cell', { name: '5' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Ver historial de plancha #4' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Dar de baja plancha #4' })).toBeEnabled()
    expect(fetch).toHaveBeenCalledTimes(5)
    expect(fetch.mock.calls[3][0]).toMatch(/\/api\/inventory\/planchas\/4$/)
    expect(fetch.mock.calls[3][1].method).toBe('PATCH')
    expect(JSON.parse(fetch.mock.calls[3][1].body)).toEqual({ cantidad: 5 })
    expect(fetch.mock.calls[4][0]).toMatch(/\/api\/inventory\/planchas$/)
    expect(fetch.mock.calls[4][1].method).toBe('GET')
  })

  test('422 muestra validación junto al formulario y conserva los datos sin refrescar', async () => {
    const { user, onSessionExpired } = await renderInventory()
    await user.click(screen.getByRole('button', { name: 'Editar' }))
    const cantidad = screen.getByRole('spinbutton', { name: /Cantidad/i })
    await user.clear(cantidad)
    await user.type(cantidad, '3')

    fetch.mockResolvedValueOnce(
      response({ detail: [{ msg: 'Validación inválida' }] }, 422),
    )
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Revisa los datos ingresados.')
    expect(alert).toBeVisible()
    expect(cantidad).toBeVisible()
    expect(cantidad).toHaveValue(3)
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeEnabled()
    expect(onSessionExpired).not.toHaveBeenCalled()
    // Solo los tres GET iniciales y el PATCH fallido; ningún refresco.
    expect(fetch).toHaveBeenCalledTimes(4)
    const [url, options] = fetch.mock.calls[3]
    expect(url).toMatch(/\/api\/inventory\/planchas\/4$/)
    expect(options.method).toBe('PATCH')
    expect(JSON.parse(options.body)).toEqual({ cantidad: 3 })
  })

  test('solo ofrece historial, edición y baja, sin toggles de estado', async () => {
    await renderInventory()
    expect(screen.queryByRole('button', { name: /^(Activar|Desactivar)$/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Editar' })).toBeVisible()
    expect(screen.getByRole('button', { name: /Dar de baja plancha/ })).toBeVisible()
  })

})

describe('TA-011 — estados de carga de Inventario', () => {
  test('muestra loading y después inventario vacío en ambas pestañas', async () => {
    let resolvePlanchas
    fetch
      .mockResolvedValueOnce(response(catalogo))
      .mockImplementationOnce(() => new Promise((resolve) => { resolvePlanchas = resolve }))
      .mockResolvedValueOnce(response([]))
    const user = userEvent.setup()
    render(<InventoryPage user={withPermissions({ rol: 'Almacenero' })} onSessionExpired={vi.fn()} />)

    expect(screen.getByRole('status')).toHaveTextContent('Cargando inventario...')
    expect(screen.queryByText('No hay planchas registradas.')).not.toBeInTheDocument()
    await act(async () => resolvePlanchas(response([])))

    expect(screen.queryByText('Cargando inventario...')).not.toBeInTheDocument()
    expect(screen.getByText('No hay planchas registradas.')).toBeVisible()
    await user.click(screen.getByRole('tab', { name: 'Retazos' }))
    expect(screen.getByText('No hay retazos registrados.')).toBeVisible()
    expect(screen.queryByText('No hay resultados para los filtros seleccionados.')).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  test('un fallo de red muestra error de carga sin presentarlo como inventario vacío', async () => {
    fetch.mockRejectedValue(new TypeError('offline'))
    const onSessionExpired = vi.fn()
    render(<InventoryPage user={withPermissions({ rol: 'Almacenero' })} onSessionExpired={onSessionExpired} />)

    const alert = await screen.findByRole('alert')
    expect(alert).toBeVisible()
    expect(alert).toHaveTextContent('No se pudo cargar el inventario')
    expect(alert).toHaveTextContent('No se pudo conectar con el servidor.')
    expect(screen.queryByText('Cargando inventario...')).not.toBeInTheDocument()
    expect(screen.queryByText('No hay planchas registradas.')).not.toBeInTheDocument()
    expect(onSessionExpired).not.toHaveBeenCalled()
  })
})
