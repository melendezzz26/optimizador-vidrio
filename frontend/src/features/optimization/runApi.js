import { API_URL } from '../../shared/apiUrl';
import { getAccessToken } from '../authentication/authApi';
import { getOrder } from '../orders/ordersApi';
import { detectMaterialGroups } from './materialGroups';
import { pieceCount } from './optimizationModel';
import { createRunTransport } from './runTransport';
import { parseMaskDescriptor, parseVisualManifest, parseVisualMask, readVisualNdjson } from './visualContract';

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
export function createBackendRunAdapter({ token, fetchImpl = globalThis.fetch, readOrder = getOrder, streamProfile = 'v1' } = {}) {
  if (!['v1', 'visual-v2'].includes(streamProfile)) throw new RunApiError('Perfil visual inválido.', 422, 'INVALID_INPUT');
  async function boundedJson(response, maximum) {
    if (!maximum) return response.json();
    const reader = response.body.getReader(), decoder = new TextDecoder('utf-8', { fatal: true });
    let length = 0, text = '';
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        length += value.byteLength;
        if (length > maximum) throw new RunApiError('El detalle visual excede el tamaño permitido.', 422, 'INVALID_INPUT');
        text += decoder.decode(value, { stream: true });
      }
      return JSON.parse(text + decoder.decode());
    } finally { await reader.cancel(); reader.releaseLock(); }
  }
  async function request(path, { method = 'GET', body, signal, stream = false, maxBytes } = {}) {
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
      const data = await boundedJson(response, maxBytes).catch(() => null);
      if (data?.detail?.code === 'CONFIG_CONFLICT') {
        console.error('No se pudo iniciar el cálculo de corte', { status: response.status, code: data.detail.code, detail: data.detail.message });
        throw new RunApiError('No se puede calcular el corte porque faltan los parámetros de trabajo. Solicita al administrador revisar la configuración.', response.status, 'CONFIG_CONFLICT');
      }
      throw new RunApiError(data?.detail?.message ?? messages[response.status]
        ?? 'El servidor no pudo completar la operación.', response.status, data?.detail?.code,
      { limit: data?.detail?.limit ?? null, retryAfter: retryAfterSeconds(response) });
    }
    if (!stream) return boundedJson(response, maxBytes);
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
  const transport = createRunTransport({
    ...(streamProfile === 'visual-v2' ? { decode: readVisualNdjson } : {}),
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
    open: (body, { signal }) => request(streamProfile === 'visual-v2' ? '?stream_profile=visual-v2' : '', { method: 'POST', body, signal, stream: true }),
    load: (id, { signal } = {}) => request(`/${encodeURIComponent(id)}`, { signal }),
    confirm: id => request(`/${encodeURIComponent(id)}/confirm`, { method: 'POST' }),
  });
  return {
    ...transport,
    async loadVisualManifest(id, { offset = 0, signal } = {}) {
      if (!Number.isSafeInteger(id) || id <= 0 || !Number.isSafeInteger(offset) || offset < 0 || offset > 1024) throw new RunApiError('Consulta visual inválida.', 422, 'INVALID_INPUT');
      return parseVisualManifest(await request(`/${id}/visual?offset=${offset}`, { signal, maxBytes: 262144 }), id);
    },
    async loadVisualMask(id, descriptor, { signal, ...window } = {}) {
      parseMaskDescriptor(descriptor, id);
      if (!descriptor.available) throw new RunApiError('Detalle visual no disponible.', 410, 'VISUAL_DATA_UNAVAILABLE');
      const query = new URLSearchParams();
      for (const [key, value] of Object.entries(window)) {
        if (!['row_start', 'row_count', 'column_start', 'column_count'].includes(key) || !Number.isSafeInteger(value)
          || value < (key.endsWith('_count') ? 1 : 0)
          || key === 'row_count' && value > 256 || key === 'column_count' && value > 1024) throw new RunApiError('Ventana visual inválida.', 422, 'INVALID_INPUT');
        query.set(key, value);
      }
      const value = parseVisualMask(await request(`/${id}/visual/masks/${descriptor.mask_ref}?${query}`, { signal, maxBytes: 262144 }), id, descriptor);
      for (const [key, expected] of Object.entries(window)) if (value.window[key] !== expected) throw new RunApiError('La máscara no corresponde a la ventana solicitada.', 422, 'INVALID_INPUT');
      return value;
    },
  };
}
