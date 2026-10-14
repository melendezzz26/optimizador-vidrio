import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import App from '../../App'

vi.mock('@formkit/auto-animate/react', () => ({ useAutoAnimate: () => [null] }))
vi.mock('../../features/authentication', () => ({
  useSession: () => ({ session: { token: 'synthetic', usuario: { rol: 'Administrador' } }, isChecking: false }),
  canManageOrders: () => true,
  canManagePlanchas: () => true,
  canManageRetazos: () => true,
  canManageUsers: () => false,
  canViewInventory: () => false,
  SessionBar: () => null,
  LoginForm: () => null,
}))

afterEach(() => {
  vi.unstubAllGlobals()
  window.history.replaceState({}, '', '/')
})

test('Pages abre el editor dentro de pedidos sin abandonar el subpath', async () => {
  window.history.replaceState({}, '', '/optimizador-vidrio/')
  vi.stubGlobal('fetch', vi.fn(async (url) => ({
    ok: true, status: 200,
    json: async () => String(url).includes('tipos-vidrio') ? [] : { items: [], total: 0, total_pages: 0 },
  })))
  const user = userEvent.setup()
  render(<App />)
  await user.click(await screen.findByRole('button', { name: 'Nuevo pedido', exact: true }))
  await screen.findByText('No hay piezas agregadas')
  await user.click(screen.getByRole('button', { name: 'Agregar pieza' }))
  await user.selectOptions(screen.getByLabelText('Forma'), 'POLIGONO_CONVEXO')
  expect(screen.getByRole('dialog', { name: 'Dibujar Polígono Convexo' })).toBeVisible()
  expect(window.location.pathname).toBe('/optimizador-vidrio/')
  await user.click(screen.getByRole('button', { name: 'Cerrar editor de polígono' }))
  expect(screen.queryByRole('dialog', { name: 'Dibujar Polígono Convexo' })).not.toBeInTheDocument()
  expect(window.location.pathname).toBe('/optimizador-vidrio/')
})
