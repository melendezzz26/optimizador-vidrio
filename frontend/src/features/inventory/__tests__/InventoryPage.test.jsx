import { act, render, screen, within } from '@testing-library/react'
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

const retazos = [
  {
    id_retazo: 9,
    codigo: 'R-9',
    id_tipo_vidrio: 1,
    espesor_mm: 6,
    geometria: { type: 'RECTANGULO', width_mm: 400, height_mm: 250 },
    area_mm2: 100000,
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

  await screen.findByRole('button', {
    name: planchaRows.some((row) => row.estado) ? /Desactivar/i : /Activar/i,
  })

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
    expect(screen.getByRole('alertdialog', { name: '¿Desactivar material?' })).toBeVisible()
    await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Desactivar' }))

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

  test('cancelar desactivación cierra el diálogo sin enviar PATCH ni cambiar estado', async () => {
    const { user } = await renderInventory()
    const button = screen.getByRole('button', { name: /Desactivar/i })
    await user.click(button)
    expect(screen.getByRole('alertdialog', { name: '¿Desactivar material?' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(screen.getByRole('cell', { name: 'Activo' })).toBeVisible()
    expect(button).toHaveFocus()
  })

  test('activar un material inactivo conserva el PATCH inmediato sin confirmación', async () => {
    const inactivePlanchas = planchas.map((row) => ({ ...row, estado: false }))
    const { user } = await renderInventory(vi.fn(), [], inactivePlanchas)
    fetch
      .mockResolvedValueOnce(response({ estado: true }))
      .mockResolvedValueOnce(response(planchas))

    await user.click(screen.getByRole('button', { name: 'Activar' }))

    expect(await screen.findByText('Plancha activada correctamente.')).toBeVisible()
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(5)
    const [url, options] = fetch.mock.calls[3]
    expect(url).toMatch(/\/api\/inventory\/planchas\/4$/)
    expect(options.method).toBe('PATCH')
    expect(JSON.parse(options.body)).toEqual({ estado: true })
  })

  test.each([
    ['plancha', 'planchas', /Desactivar/i, /\/api\/inventory\/planchas\/4$/],
    ['retazo', 'retazos', /Desactivar/i, /\/api\/inventory\/retazos\/9$/],
  ])('confirmar desactivación de %s realiza un PATCH y refresca el listado', async (_kind, tab, buttonName, endpoint) => {
    const { user } = await renderInventory(vi.fn(), retazos)
    if (tab === 'retazos') await user.click(screen.getByRole('tab', { name: 'Retazos' }))
    await user.click(screen.getByRole('button', { name: buttonName }))
    fetch
      .mockResolvedValueOnce(response({ estado: false }))
      .mockResolvedValueOnce(response(tab === 'planchas' ? planchas.map((row) => ({ ...row, estado: false })) : retazos.map((row) => ({ ...row, estado: false }))));
    await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Desactivar' }))

    const feedback = tab === 'planchas' ? 'Plancha desactivada correctamente.' : 'Retazo desactivado correctamente.'
    expect(await screen.findByText(feedback)).toBeVisible()
    expect(fetch).toHaveBeenCalledTimes(5)
    const [url, options] = fetch.mock.calls[3]
    expect(url).toMatch(endpoint)
    expect(options.method).toBe('PATCH')
    expect(JSON.parse(options.body)).toEqual({ estado: false })
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
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
