import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { InventoryPage } from '../InventoryPage'

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

async function renderInventory(onSessionExpired = vi.fn()) {
  fetch
    .mockResolvedValueOnce(response(catalogo))
    .mockResolvedValueOnce(response(planchas))
    .mockResolvedValueOnce(response([]))

  const user = userEvent.setup()

  render(
    <InventoryPage
      user={{
        id_usuario: 4,
        username: 'A00000001',
        nombre: 'Cuenta Prueba Almacen',
        rol: 'Almacenero',
      }}
      toolbar={<div>Toolbar</div>}
      onSessionExpired={onSessionExpired}
    />,
  )

  await screen.findByRole('button', { name: /Desactivar/i })

  return { user, onSessionExpired }
}

describe('TA-011 — errores HTTP de Inventario', () => {
  test('403 muestra error de permisos, conserva sesión y no refresca el listado', async () => {
    const { user, onSessionExpired } = await renderInventory()

    fetch.mockResolvedValueOnce(
      response(
        { detail: 'No tienes el permiso: GESTIONAR_PLANCHAS' },
        403,
      ),
    )

    await user.click(
      screen.getByRole('button', { name: /Desactivar/i }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No tienes el permiso: GESTIONAR_PLANCHAS',
    )

    expect(onSessionExpired).not.toHaveBeenCalled()

    expect(fetch).toHaveBeenCalledTimes(4)

    const [url, options] = fetch.mock.calls[3]

    expect(url).toMatch(/\/api\/inventory\/planchas\/4$/)
    expect(options.method).toBe('PATCH')
    expect(options.headers.Authorization).toBe('Bearer test-token')
    expect(JSON.parse(options.body)).toEqual({ estado: false })

    // Al fallar el PATCH no debe ejecutarse GET /planchas posterior.
    expect(fetch).toHaveBeenCalledTimes(4)

    // El estado visible tampoco debe cambiar.
    expect(screen.getByRole('cell', { name: 'Activo' })).toBeVisible()

    expect(
    screen.getByRole('button', { name: /Desactivar/i }),
    ).toBeEnabled()

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
})

describe('TA-011 — estados de carga de Inventario', () => {
  test('muestra loading y después inventario vacío en ambas pestañas', async () => {
    let resolvePlanchas
    fetch
      .mockResolvedValueOnce(response(catalogo))
      .mockImplementationOnce(() => new Promise((resolve) => { resolvePlanchas = resolve }))
      .mockResolvedValueOnce(response([]))
    const user = userEvent.setup()
    render(<InventoryPage user={{ rol: 'Almacenero' }} onSessionExpired={vi.fn()} />)

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
    render(<InventoryPage user={{ rol: 'Almacenero' }} onSessionExpired={onSessionExpired} />)

    const alert = await screen.findByRole('alert')
    expect(alert).toBeVisible()
    expect(alert).toHaveTextContent('No se pudo cargar el inventario')
    expect(alert).toHaveTextContent('No se pudo conectar con el servidor.')
    expect(screen.queryByText('Cargando inventario...')).not.toBeInTheDocument()
    expect(screen.queryByText('No hay planchas registradas.')).not.toBeInTheDocument()
    expect(onSessionExpired).not.toHaveBeenCalled()
  })
})
