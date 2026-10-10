import { API_URL } from '../../shared/apiUrl';
import { getAccessToken } from '../authentication';

const STATUS_MESSAGES = {
  401: 'Tu sesión venció. Inicia sesión otra vez.',
  403: 'No tienes permiso para realizar esta operación.',
  404: 'El pedido solicitado ya no está disponible.',
  409: 'El pedido cambió mientras lo editabas. Actualiza la vista e inténtalo otra vez.',
  500: 'El servidor no pudo completar la operación. Inténtalo otra vez.',
};

export class OrdersApiError extends Error {
  constructor(message, status, options = {}) {
    super(message, options);
    this.name = 'OrdersApiError';
    this.status = status;
  }
}

async function request(path, { method = 'GET', body, signal, token, validationFallback } = {}) {
  const accessToken = token ?? getAccessToken();
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      signal,
      headers: {
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new OrdersApiError(
      'No se pudo conectar con el servidor. Revisa la conexión e inténtalo otra vez.',
      0,
      { cause: error },
    );
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message = response.status === 422
      ? (typeof data?.detail === 'string' ? data.detail : validationFallback ?? 'Revisa los datos del pedido e inténtalo otra vez.')
      : STATUS_MESSAGES[response.status] ?? 'No se pudo completar la solicitud. Inténtalo otra vez.';
    throw new OrdersApiError(message, response.status);
  }
  if (!data) throw new OrdersApiError('El servidor devolvió una respuesta inesperada.', response.status);
  return data;
}

export const listOrderMaterials = ({ signal, token } = {}) =>
  request('/api/inventory/tipos-vidrio', { signal, token });

export const createOrder = (body, { signal, token } = {}) =>
  request('/api/orders', {
    method: 'POST', body, signal, token,
    validationFallback: 'No se pudo registrar el pedido. Revisa las piezas e inténtalo de nuevo.',
  });

export const listOrders = ({ page = 1, limit = 10, estado, cliente, fecha } = {}, { signal, token } = {}) => {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (estado) params.set('estado', estado);
  if (cliente) params.set('cliente', cliente);
  if (fecha) params.set('fecha', fecha);
  return request(`/api/orders?${params}`, { signal, token });
};

export const getOrder = (idPedido, { signal, token } = {}) =>
  request(`/api/orders/${encodeURIComponent(idPedido)}`, { signal, token });

export const updateOrder = (idPedido, body, { signal, token } = {}) =>
  request(`/api/orders/${encodeURIComponent(idPedido)}`, {
    method: 'PUT', body, signal, token,
    validationFallback: 'No se pudo actualizar el pedido. Revisa las piezas e inténtalo de nuevo.',
  });

export const cancelOrder = (idPedido, { signal, token } = {}) =>
  request(`/api/orders/${encodeURIComponent(idPedido)}`, { method: 'DELETE', signal, token });
