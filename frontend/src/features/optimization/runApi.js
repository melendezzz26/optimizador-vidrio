import { API_URL } from '../../shared/apiUrl';
import { getAccessToken } from '../authentication/authApi';
import { getOrder } from '../orders/ordersApi';
import { detectMaterialGroups } from './materialGroups';
import { pieceCount } from './optimizationModel';
import { createRunTransport } from './runTransport';

export class RunApiError extends Error {
  constructor(message, status, code, { limit = null, retryAfter = null } = {}) {
    super(message);
    this.name = 'RunApiError';
    this.status = status;
    this.code = code;
    // TA-037: which operational limit was exceeded and when to retry (503).
    this.limit = limit;
    this.retryAfter = retryAfter;
  }
}

function retryAfterSeconds(response) {
  const value = Number(response.headers?.get?.('retry-after'));
  return Number.isSafeInteger(value) && value > 0 ? value : null;
}

const messages = {
  401: 'Tu sesión venció. Inicia sesión otra vez.',
  403: 'No tienes permiso para realizar esta operación.',
  404: 'El trabajo o alguno de los pedidos ya no está disponible.',
  409: 'El trabajo o las existencias cambiaron. Revisa el resultado antes de continuar.',
  422: 'No se puede completar la operación con los datos actuales.',
};

// All URLs come from the implemented v1 routes. Never follow an event-provided
// URL to another host, and never send a replacement layout on confirmation.
export function createBackendRunAdapter({ token, fetchImpl = globalThis.fetch, readOrder = getOrder } = {}) {
  async function request(path, { method = 'GET', body, signal, stream = false } = {}) {
    let response;
    try {
      const accessToken = token ?? getAccessToken();
      response = await fetchImpl(`${API_URL}/api/optimization/runs${path}`, {
        method, signal,
        headers: {
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
          Accept: stream ? 'application/x-ndjson' : 'application/json',
        },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new RunApiError('No se pudo conectar. Consulta el resultado antes de preparar otro trabajo.', 0, 'NETWORK_ERROR');
    }
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      if (data?.detail?.code === 'CONFIG_CONFLICT') {
        console.error('No se pudo iniciar el cálculo de corte', { status: response.status, code: data.detail.code, detail: data.detail.message });
        throw new RunApiError('No se puede calcular el corte porque faltan los parámetros de trabajo. Solicita al administrador revisar la configuración.', response.status, 'CONFIG_CONFLICT');
      }
      throw new RunApiError(data?.detail?.message ?? messages[response.status]
        ?? 'El servidor no pudo completar la operación.', response.status, data?.detail?.code,
      { limit: data?.detail?.limit ?? null, retryAfter: retryAfterSeconds(response) });
    }
    if (!stream) return response.json();
    if (!response.headers.get('content-type')?.startsWith('application/x-ndjson') || !response.body) {
      throw new RunApiError('No se pudo seguir el avance del trabajo. Consulta el resultado antes de continuar.', response.status, 'INVALID_STREAM');
    }
    const chunks = (async function* () {
      const reader = response.body.getReader();
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          yield value;
        }
      } finally { await reader.cancel(); reader.releaseLock(); }
    })();
    // Acceptance is durable before the first body chunk. Retain the canonical
    // ID even if the connection fails before optimization_started is decoded.
    const location = response.headers.get('location');
    const match = location?.match(/^\/api\/optimization\/runs\/([1-9]\d*)$/);
    if (match && Number.isSafeInteger(Number(match[1]))) chunks.optimizationId = Number(match[1]);
    return chunks;
  }
  return createRunTransport({
    async prepare({ order_ids }) {
      // Read-only preview, never /start or inventory reservation. The run POST
      // revalidates the complete selection atomically on the server.
      const orders = await Promise.all(order_ids.map(id => readOrder(id, { token })));
      if (orders.some((o, i) => o.id_pedido !== order_ids[i] || o.estado !== 'PENDIENTE')) {
        throw new RunApiError('La selección cambió. Actualiza los pedidos pendientes.', 409, 'STATE_CONFLICT');
      }
      const { groups, unresolved } = detectMaterialGroups(orders);
      if (unresolved.length) throw new RunApiError('Falta el detalle de las piezas seleccionadas.', 422, 'INVALID_INPUT');
      return { orders, groups, total: pieceCount(orders), rasters: {} };
    },
    open: (body, { signal }) => request('', { method: 'POST', body, signal, stream: true }),
    load: (id, { signal } = {}) => request(`/${encodeURIComponent(id)}`, { signal }),
    confirm: id => request(`/${encodeURIComponent(id)}/confirm`, { method: 'POST' }),
  });
}
