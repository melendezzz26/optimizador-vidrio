import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { InventoryPage } from '../InventoryPage'

const catalog = [{ id_tipo_vidrio: 1, nombre: 'Incoloro', estado: true, espesores_mm: [6] }]
const plancha = {
  id_plancha: 4,
  id_tipo_vidrio: 1,
  espesor_mm: 6,
  ancho_mm: 1000,
  alto_mm: 500,
  cantidad: 2,
  estado: true,
  fecha_registro: '2026-10-08T12:00:00Z',
}
const retazo = {
  id_retazo: 9,
  codigo: 'R-9',
  id_tipo_vidrio: 1,
  espesor_mm: 6,
  geometria: { type: 'RECTANGULO', width_mm: 400, height_mm: 250 },
  area_mm2: 100000,
  estado: true,
  fecha_registro: '2026-10-08T12:00:00Z',
}
const historyMovement = {
  id_movimiento: 22,
  id_plancha: 4,
  id_retazo: null,
  tipo_evento: 'BAJA_MERMA',
  motivo: 'Borde astillado',
  observacion: 'Separado del lote',
  id_usuario: 4,
  fecha: '2026-10-10T12:30:00Z',
  id_optimizacion: 17,
}

function response(data, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => data }
}

function sessionFor(rol) {
  sessionStorage.setItem('optimizador.auth', JSON.stringify({
    access_token: 'component-test-token',
    usuario: { id_usuario: 4, username: 'A00000004', nombre: 'Almacén', rol },
  }))
}

async function renderInventory({
  rol = 'Almacenero',
  planchas = [plancha],
  retazos = [retazo],
  onSessionExpired = vi.fn(),
} = {}) {
  sessionFor(rol)
  fetch
    .mockResolvedValueOnce(response(catalog))
    .mockResolvedValueOnce(response(planchas))
    .mockResolvedValueOnce(response(retazos))
  const user = userEvent.setup()
  render(<InventoryPage user={{ id_usuario: 4, nombre: 'Almacén', rol }} onSessionExpired={onSessionExpired} />)
  await screen.findByText(`Mostrando 1 de 1 planchas`)
  return { user, onSessionExpired }
}

async function openWriteoff(user, kind = 'plancha') {
  const buttonName = kind === 'plancha' ? 'Dar de baja plancha #4' : 'Dar de baja retazo R-9'
  await user.click(screen.getByRole('button', { name: buttonName }))
  const dialog = screen.getByRole('dialog', { name: `Dar de baja ${kind}` })
  expect(screen.getByLabelText('Tipo de baja')).toHaveFocus()
  return dialog
}

async function fillWriteoff(user, { reason = 'Borde dañado', event = 'BAJA_ROTURA', observation = '' } = {}) {
  await user.selectOptions(screen.getByLabelText('Tipo de baja'), event)
  if (reason) await user.type(screen.getByLabelText(/Motivo/), reason)
  if (observation) await user.type(screen.getByLabelText('Observación (opcional)'), observation)
  const quantity = screen.queryByLabelText('Cantidad a dar de baja')
  if (quantity) { await user.clear(quantity); await user.type(quantity, '2') }
  await user.click(screen.getByRole('button', { name: 'Revisar baja' }))
  return screen.getByRole('dialog', { name: 'Confirmar baja manual' })
}

beforeEach(() => {
  sessionStorage.clear()
  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  vi.unstubAllGlobals()
  sessionStorage.clear()
})

describe('HU-014: permisos y apertura', () => {
  test('gestor ve baja e historial; operario consulta historial pero no gestiona bajas', async () => {
    await renderInventory({ rol: 'Almacenero' })
    expect(screen.getByRole('button', { name: 'Dar de baja plancha #4' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Ver historial de plancha #4' })).toBeVisible()

    cleanup()
    await renderInventory({ rol: 'Operario' })
    expect(screen.queryByRole('button', { name: 'Dar de baja plancha #4' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ver historial de plancha #4' })).toBeVisible()
  })

  test('un rol sin CONSULTAR_STOCK no ve historial ni acciones de gestión', async () => {
    await renderInventory({ rol: 'Invitado' })
    expect(screen.queryByRole('button', { name: 'Ver historial de plancha #4' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Dar de baja plancha #4' })).not.toBeInTheDocument()
  })

  test.each([
    ['plancha', 'Dar de baja plancha', /Incoloro.*6 mm.*1,000.*500/],
    ['retazo', 'Dar de baja retazo', /R-9.*Incoloro.*6 mm.*Rectángulo/],
  ])('abre el diálogo identificado para %s, con nombre accesible y foco inicial', async (kind, title, detail) => {
    const { user } = await renderInventory()
    if (kind === 'retazo') await user.click(screen.getByRole('tab', { name: 'Retazos' }))
    const dialog = await openWriteoff(user, kind)
    expect(dialog).toHaveAccessibleName(title)
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(within(dialog).getByText(detail)).toBeVisible()
  })
})

describe('HU-014: formulario y confirmación de baja', () => {
  test('selector manual contiene solo los cuatro eventos admitidos', async () => {
    const { user } = await renderInventory()
    const dialog = await openWriteoff(user)
    const options = within(screen.getByLabelText('Tipo de baja')).getAllByRole('option')
    expect(options.map((option) => option.value)).toEqual([
      'BAJA_ROTURA', 'BAJA_MERMA', 'BAJA_ERROR_REGISTRO', 'BAJA_RETIRO',
    ])
    expect(within(dialog).queryByRole('option', { name: /optimización/i })).not.toBeInTheDocument()
  })

  test('motivo obligatorio bloquea el avance si está vacío o solo contiene espacios', async () => {
    const { user } = await renderInventory()
    await openWriteoff(user)
    await user.click(screen.getByRole('button', { name: 'Revisar baja' }))
    expect(screen.getByRole('dialog', { name: 'Dar de baja plancha' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Confirmar baja' })).not.toBeInTheDocument()

    await user.type(screen.getByLabelText(/Motivo/), '   ')
    await user.click(screen.getByRole('button', { name: 'Revisar baja' }))
    expect(screen.getByRole('alert')).toHaveTextContent('El motivo es obligatorio.')
    expect(screen.queryByRole('button', { name: 'Confirmar baja' })).not.toBeInTheDocument()
  })

  test('primer clic abre revisión sin POST; muestra material, evento, motivo y efecto', async () => {
    const { user } = await renderInventory()
    await openWriteoff(user)
    expect(fetch.mock.calls.some(([url]) => String(url).includes('/baja'))).toBe(false)
    const dialog = await fillWriteoff(user, {
      event: 'BAJA_MERMA', reason: 'Pérdida de material', observation: 'Esquina dañada',
    })
    expect(dialog).toHaveTextContent('Incoloro')
    expect(dialog).toHaveTextContent('Merma')
    expect(dialog).toHaveTextContent('Pérdida de material')
    expect(dialog).toHaveTextContent('quedará inactivo')
    expect(dialog).toHaveTextContent('No se eliminará')
    expect(fetch.mock.calls.some(([url]) => String(url).includes('/baja'))).toBe(false)
  })

  test('observación es opcional y el payload conserva los campos permitidos', async () => {
    const { user } = await renderInventory()
    await openWriteoff(user)
    await fillWriteoff(user, { reason: 'Merma del material', event: 'BAJA_MERMA' })
    fetch
      .mockResolvedValueOnce(response({ estado: false, movimiento: { id_movimiento: 31 } }, 201))
      .mockResolvedValueOnce(response([{ ...plancha, estado: false }]))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))
    await screen.findByText(/Baja registrada correctamente/)
    const post = fetch.mock.calls.find(([url]) => String(url).includes('/planchas/4/baja'))
    expect(JSON.parse(post[1].body)).toEqual({
      tipo_evento: 'BAJA_MERMA', motivo: 'Merma del material', observacion: null, cantidad_afectada: 2,
    })
  })

  test('confirmación dispara un POST, muestra feedback, refresca y conserva el recurso inactivo', async () => {
    const { user } = await renderInventory()
    await openWriteoff(user)
    await fillWriteoff(user, { event: 'BAJA_RETIRO', reason: 'Retiro autorizado' })
    fetch
      .mockResolvedValueOnce(response({ estado: false, movimiento: { id_movimiento: 44 } }, 201))
      .mockResolvedValueOnce(response([{ ...plancha, estado: false }]))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))

    expect(await screen.findByText('Baja registrada correctamente. Movimiento #44.')).toBeVisible()
    expect(screen.getByRole('cell', { name: 'Inactivo' })).toBeVisible()
    expect(screen.getAllByRole('row')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Ver historial de plancha #4' })).toBeVisible()
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/planchas/4/baja'))).toHaveLength(1)
    expect(fetch.mock.calls.some(([url]) => String(url).includes('/planchas/4/movimientos'))).toBe(false)
  })

  test('la baja de retazo usa su endpoint y mantiene la fila con estado inactivo', async () => {
    const { user } = await renderInventory()
    await user.click(screen.getByRole('tab', { name: 'Retazos' }))
    await openWriteoff(user, 'retazo')
    await fillWriteoff(user, { event: 'BAJA_ERROR_REGISTRO', reason: 'Código duplicado' })
    fetch
      .mockResolvedValueOnce(response({ estado: false, movimiento: { id_movimiento: 45 } }, 201))
      .mockResolvedValueOnce(response([{ ...retazo, estado: false }]))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))

    expect(await screen.findByText('Baja registrada correctamente. Movimiento #45.')).toBeVisible()
    expect(screen.getByRole('cell', { name: 'Inactivo' })).toBeVisible()
    expect(screen.getAllByRole('row')).toHaveLength(2)
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/retazos/9/baja'))).toHaveLength(1)
    expect(fetch.mock.calls.find(([url]) => String(url).includes('/retazos/9/baja'))[1].method).toBe('POST')
  })

  test('plancha no disponible impide baja parcial', async () => {
    await renderInventory({ planchas: [{ ...plancha, estado: false }] })
    expect(screen.getByRole('cell', { name: 'Inactivo' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Dar de baja plancha #4' })).toBeDisabled()
  })

  test('segunda activación durante el envío no duplica POST, bloquea cierre y muestra procesamiento', async () => {
    const { user } = await renderInventory()
    await openWriteoff(user)
    await fillWriteoff(user)
    let finishPost
    fetch.mockImplementationOnce(() => new Promise((resolve) => { finishPost = resolve }))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Registrando…' })).toBeDisabled())
    await user.click(screen.getByRole('button', { name: 'Registrando…' }))
    expect(screen.getByRole('button', { name: 'Cerrar diálogo' })).toBeDisabled()
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/planchas/4/baja'))).toHaveLength(1)
    await user.keyboard('{Escape}')
    expect(screen.getByRole('dialog', { name: 'Confirmar baja manual' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Cerrar diálogo' }))
    expect(screen.getByRole('dialog', { name: 'Confirmar baja manual' })).toBeVisible()

    fetch.mockResolvedValueOnce(response([{ ...plancha, estado: false }]))
    await act(async () => finishPost(response({ estado: false, movimiento: { id_movimiento: 51 } }, 201)))
    await screen.findByText('Baja registrada correctamente. Movimiento #51.')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('HU-014: errores y sesión', () => {
  test('409 muestra conflicto sin reintento automático ni pérdida del borrador', async () => {
    const { user } = await renderInventory()
    await openWriteoff(user)
    await fillWriteoff(user, { reason: 'Ya tuvo una baja' })
    fetch.mockResolvedValueOnce(response({ detail: 'El material ya tiene una baja manual registrada.' }, 409))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('ya tiene una baja manual')
    expect(screen.getByText('Ya tuvo una baja')).toBeVisible()
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/planchas/4/baja'))).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Confirmar baja' })).toBeEnabled()
  })

  test('422 conserva evento, motivo y observación para corregir y reintentar', async () => {
    const { user } = await renderInventory()
    await openWriteoff(user)
    await fillWriteoff(user, {
      event: 'BAJA_ERROR_REGISTRO', reason: 'Registro incorrecto', observation: 'Lote 2',
    })
    fetch.mockResolvedValueOnce(response({ detail: [{ msg: 'inválido' }] }, 422))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Revisa los datos ingresados.')
    await user.click(screen.getByRole('button', { name: 'Volver' }))
    expect(screen.getByLabelText('Tipo de baja')).toHaveValue('BAJA_ERROR_REGISTRO')
    expect(screen.getByLabelText(/Motivo/)).toHaveValue('Registro incorrecto')
    expect(screen.getByLabelText('Observación (opcional)')).toHaveValue('Lote 2')
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/planchas/4/baja'))).toHaveLength(1)
  })

  test.each([
    ['500', () => response({ detail: 'Error interno' }, 500)],
    ['red', () => { throw new TypeError('offline') }],
  ])('%s informa que la baja no fue confirmada y conserva el borrador', async (_name, makeFailure) => {
    const { user } = await renderInventory()
    await openWriteoff(user)
    await fillWriteoff(user, { reason: 'Conservar para reintento' })
    fetch.mockImplementationOnce(async () => makeFailure())
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo confirmar la baja.')
    expect(screen.getByText('Conservar para reintento')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Confirmar baja' })).toBeEnabled()
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/planchas/4/baja'))).toHaveLength(1)
    fetch
      .mockResolvedValueOnce(response({ estado: false, movimiento: { id_movimiento: 63 } }, 201))
      .mockResolvedValueOnce(response([{ ...plancha, estado: false }]))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))
    expect(await screen.findByText('Baja registrada correctamente. Movimiento #63.')).toBeVisible()
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/planchas/4/baja'))).toHaveLength(2)
  })

  test.each([
    [401, 'Sesión expirada', true],
    [403, 'Sin permiso de gestión', false],
    [404, 'Plancha inexistente', false],
  ])('HTTP %i respeta el manejo de Inventory/session', async (status, detail, expiresSession) => {
    const onSessionExpired = vi.fn()
    const { user } = await renderInventory({ onSessionExpired })
    await openWriteoff(user)
    await fillWriteoff(user)
    fetch.mockResolvedValueOnce(response({ detail }, status))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(detail)
    expect(onSessionExpired).toHaveBeenCalledTimes(expiresSession ? 1 : 0)
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/planchas/4/baja'))).toHaveLength(1)
  })
})

describe('HU-014: historial', () => {
  test.each([
    ['plancha', '/api/inventory/planchas/4/movimientos'],
    ['retazo', '/api/inventory/retazos/9/movimientos'],
  ])('abre historial de %s, muestra loading y usa el endpoint correcto', async (kind, path) => {
    const { user } = await renderInventory()
    if (kind === 'retazo') await user.click(screen.getByRole('tab', { name: 'Retazos' }))
    let finishHistory
    fetch.mockImplementationOnce(() => new Promise((resolve) => { finishHistory = resolve }))
    const buttonName = kind === 'plancha' ? 'Ver historial de plancha #4' : 'Ver historial de retazo R-9'
    await user.click(screen.getByRole('button', { name: buttonName }))
    expect(screen.getByText('Cargando historial de movimientos...')).toBeVisible()
    expect(screen.getByRole('dialog', { name: /Historial de movimientos/ })).toHaveAttribute('aria-modal', 'true')
    expect(fetch.mock.calls.at(-1)[0]).toContain(path)
    await act(async () => finishHistory(response([historyMovement])))
    expect(await screen.findByText('Baja por merma')).toBeVisible()
  })

  test('lista vacía usa el mensaje definido para el material', async () => {
    const { user } = await renderInventory()
    fetch.mockResolvedValueOnce(response([]))
    await user.click(screen.getByRole('button', { name: 'Ver historial de plancha #4' }))
    expect(await screen.findByText('No hay movimientos registrados para este material.')).toBeVisible()
  })

  test('muestra evento, motivo, observación nula, actor, fecha y optimización', async () => {
    const { user } = await renderInventory()
    fetch.mockResolvedValueOnce(response([{ ...historyMovement, observacion: null }]))
    await user.click(screen.getByRole('button', { name: 'Ver historial de plancha #4' }))
    const dialog = screen.getByRole('dialog', { name: /Historial de movimientos/ })
    expect(await within(dialog).findByText('Baja por merma')).toBeVisible()
    expect(dialog).toHaveTextContent('Borde astillado')
    expect(dialog).toHaveTextContent('Sin observación')
    expect(dialog).toHaveTextContent('Usuario #4')
    expect(dialog).toHaveTextContent('#17')
    expect(dialog.querySelector('time')).toHaveAttribute('dateTime', historyMovement.fecha)
  })

  test('error de historial permite reintentar sin cerrar el diálogo', async () => {
    const { user } = await renderInventory()
    fetch
      .mockResolvedValueOnce(response({ detail: 'Fallo temporal' }, 500))
      .mockResolvedValueOnce(response([historyMovement]))
    await user.click(screen.getByRole('button', { name: 'Ver historial de plancha #4' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Fallo temporal')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByText('Baja por merma')).toBeVisible()
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/planchas/4/movimientos'))).toHaveLength(2)
  })

  test('respuesta antigua no reemplaza el historial de la solicitud más reciente', async () => {
    const { user } = await renderInventory()
    let finishOldRequest
    fetch.mockImplementationOnce(() => new Promise((resolve) => { finishOldRequest = resolve }))
    await user.click(screen.getByRole('button', { name: 'Ver historial de plancha #4' }))
    await user.click(screen.getByRole('button', { name: 'Cerrar diálogo' }))
    await user.click(screen.getByRole('tab', { name: 'Retazos' }))
    fetch.mockResolvedValueOnce(response([{ ...historyMovement, id_retazo: 9, id_plancha: null, motivo: 'Respuesta nueva' }]))
    await user.click(screen.getByRole('button', { name: 'Ver historial de retazo R-9' }))
    expect(await screen.findByText('Respuesta nueva')).toBeVisible()
    await act(async () => finishOldRequest(response([{ ...historyMovement, motivo: 'Respuesta antigua' }])))
    expect(screen.getByText('Respuesta nueva')).toBeVisible()
    expect(screen.queryByText('Respuesta antigua')).not.toBeInTheDocument()
  })
})

describe('HU-014: accesibilidad', () => {
  test('Escape cierra y restaura foco; Tab y Shift+Tab mantienen foco dentro del diálogo', async () => {
    const { user } = await renderInventory()
    const trigger = screen.getByRole('button', { name: 'Dar de baja plancha #4' })
    await user.click(trigger)
    const dialog = screen.getByRole('dialog', { name: 'Dar de baja plancha' })
    const close = within(dialog).getByRole('button', { name: 'Cerrar diálogo' })
    close.focus()
    await user.keyboard('{Shift>}{Tab}{/Shift}')
    expect(within(dialog).getByRole('button', { name: 'Revisar baja' })).toHaveFocus()
    await user.keyboard('{Tab}')
    expect(close).toHaveFocus()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  test('controles del formulario tienen nombres y el cierre es disabled durante el envío', async () => {
    const { user } = await renderInventory()
    const dialog = await openWriteoff(user)
    expect(within(dialog).getByLabelText('Tipo de baja')).toBeVisible()
    expect(within(dialog).getByLabelText(/Motivo/)).toBeVisible()
    expect(within(dialog).getByLabelText('Observación (opcional)')).toBeVisible()
    await fillWriteoff(user)
    let finishPost
    fetch.mockImplementationOnce(() => new Promise((resolve) => { finishPost = resolve }))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Cerrar diálogo' })).toBeDisabled())
    expect(screen.getByRole('dialog', { name: 'Confirmar baja manual' })).toHaveAttribute('aria-busy', 'true')
    fetch.mockResolvedValueOnce(response([{ ...plancha, estado: false }]))
    await act(async () => finishPost(response({ estado: false, movimiento: { id_movimiento: 60 } }, 201)))
    await screen.findByText(/Baja registrada correctamente/)
  })
})

describe('TA-036: baja parcial y cantidades', () => {
  test('actualiza saldo confirmado aunque falle refresco, conserva historial y disponibilidad', async () => {
    const { user } = await renderInventory({ planchas: [{ ...plancha, cantidad: 10 }] })
    await openWriteoff(user)
    expect(screen.getByText('Cantidad disponible actual: 10')).toBeVisible()
    await user.type(screen.getByLabelText(/Motivo/), 'Rotura de una unidad')
    expect(screen.getByText('Cantidad restante: 9')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Revisar baja' }))
    expect(screen.getByRole('dialog')).toHaveTextContent('Cantidad restante9')
    fetch.mockResolvedValueOnce(response({ estado: true, cantidad: 9, movimiento: { id_movimiento: 90 } }, 201))
      .mockRejectedValueOnce(new Error('offline'))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))
    await screen.findByText(/no se pudo actualizar el listado/)
    expect(screen.getByRole('cell', { name: '9' })).toBeVisible()
    expect(screen.getByRole('cell', { name: 'Activo' })).toBeVisible()
    expect(screen.getByRole('button', { name: /Dar de baja plancha/ })).toBeEnabled()
    expect(JSON.parse(fetch.mock.calls[3][1].body).cantidad_afectada).toBe(1)
    expect(screen.queryByRole('button', { name: /^(Activar|Desactivar)$/ })).not.toBeInTheDocument()
  })

  test.each(['0', '11', '1.5'])('cantidad inválida %s no avanza a confirmación', async (value) => {
    const { user } = await renderInventory({ planchas: [{ ...plancha, cantidad: 10 }] })
    await openWriteoff(user)
    await user.type(screen.getByLabelText(/Motivo/), 'Motivo')
    await user.clear(screen.getByLabelText('Cantidad a dar de baja'))
    await user.type(screen.getByLabelText('Cantidad a dar de baja'), value)
    await user.click(screen.getByRole('button', { name: 'Revisar baja' }))
    expect(screen.queryByRole('button', { name: 'Confirmar baja' })).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  test('retazo no solicita cantidad editable y queda detrás del disponible tras baja', async () => {
    const { user } = await renderInventory({ retazos: [retazo, { ...retazo, id_retazo: 10, codigo: 'R-10' }] })
    await user.click(screen.getByRole('tab', { name: 'Retazos' }))
    await openWriteoff(user, 'retazo')
    expect(screen.queryByLabelText('Cantidad a dar de baja')).not.toBeInTheDocument()
    await fillWriteoff(user)
    fetch.mockResolvedValueOnce(response({ estado: false, movimiento: { id_movimiento: 91 } }, 201))
      .mockRejectedValueOnce(new Error('offline'))
    await user.click(screen.getByRole('button', { name: 'Confirmar baja' }))
    await screen.findByText(/no se pudo actualizar el listado/)
    const rows = screen.getAllByRole('row').slice(1)
    expect(rows[0]).toHaveTextContent('R-10')
    expect(rows[1]).toHaveTextContent('R-9')
    expect(rows[1]).toHaveTextContent('Inactivo')
  })
})
