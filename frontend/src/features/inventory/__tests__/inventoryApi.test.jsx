import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

const payload = {
  tipo_evento: 'BAJA_MERMA',
  motivo: 'Pieza dañada',
  observacion: 'Daño en el borde',
}
const movement = {
  id_movimiento: 22,
  id_plancha: 4,
  id_retazo: null,
  tipo_evento: payload.tipo_evento,
  motivo: payload.motivo,
  observacion: payload.observacion,
  id_usuario: 4,
  fecha: '2026-10-10T12:00:00Z',
  id_optimizacion: null,
}

const endpoints = [
  {
    name: 'baja plancha',
    url: '/planchas/4/baja',
    method: 'POST',
    invoke: (api) => api.writeoffPlancha(4, payload),
    body: payload,
  },
  {
    name: 'baja retazo',
    url: '/retazos/9/baja',
    method: 'POST',
    invoke: (api) => api.writeoffRetazo(9, payload),
    body: payload,
  },
  {
    name: 'historial plancha',
    url: '/planchas/4/movimientos',
    method: 'GET',
    invoke: (api) => api.getPlanchaMovements(4),
  },
  {
    name: 'historial retazo',
    url: '/retazos/9/movimientos',
    method: 'GET',
    invoke: (api) => api.getRetazoMovements(9),
  },
]

function makeResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  }
}

let api
let apiUrl

beforeEach(async () => {
  sessionStorage.setItem('optimizador.auth', JSON.stringify({
    access_token: 'inventory-test-token', usuario: { id_usuario: 4 },
  }))
  vi.stubEnv('VITE_API_URL', 'https://inventory-api.test/')
  vi.stubGlobal('fetch', vi.fn())
  vi.resetModules()
  api = await import('../inventoryApi')
  apiUrl = (await import('../../../shared/apiUrl')).API_URL
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  sessionStorage.clear()
})

describe('inventoryApi HU-014', () => {
  for (const endpoint of endpoints) {
    test(`${endpoint.name}: usa URL VITE_API_URL, método y autorización comunes`, async () => {
      let request
      fetch.mockImplementation(async (url, options) => {
        request = { url, options }
        return makeResponse(endpoint.method === 'GET' ? [movement] : { estado: false, movimiento: movement })
      })

      const result = await endpoint.invoke(api)

      expect(apiUrl).toBe('https://inventory-api.test')
      expect(request.url).toBe(`${apiUrl}/api/inventory${endpoint.url}`)
      expect(request.options.method).toBe(endpoint.method)
      expect(request.options.headers.Authorization).toBe('Bearer inventory-test-token')
      if (endpoint.body) {
        expect(request.options.headers['Content-Type']).toBe('application/json')
        const sent = JSON.parse(request.options.body)
        expect(sent).toEqual(payload)
        expect(sent).not.toHaveProperty('id_usuario')
        expect(sent).not.toHaveProperty('fecha')
        expect(sent).not.toHaveProperty('id_optimizacion')
      } else {
        expect(request.options.body).toBeUndefined()
        expect(result).toEqual([movement])
      }
    })
  }

  for (const endpoint of endpoints) {
    const statuses = endpoint.method === 'POST' ? [401, 403, 404, 409, 422, 500] : [401, 403, 404, 422, 500]
    for (const status of statuses) {
      test(`${endpoint.name}: convierte HTTP ${status} en InventoryApiError`, async () => {
        fetch.mockResolvedValue(makeResponse({ detail: `error ${status}` }, status))
        const error = await endpoint.invoke(api).catch((caught) => caught)

        expect(error).toBeInstanceOf(api.InventoryApiError)
        expect(error).toMatchObject({ name: 'InventoryApiError', status, message: `error ${status}` })
      })
    }

    test(`${endpoint.name}: convierte error de red en InventoryApiError`, async () => {
      fetch.mockRejectedValue(new TypeError('offline'))
      const error = await endpoint.invoke(api).catch((caught) => caught)

      expect(error).toBeInstanceOf(api.InventoryApiError)
      expect(error).toMatchObject({ name: 'InventoryApiError', status: 0 })
    })
  }
})
