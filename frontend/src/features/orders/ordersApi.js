import { createApiRequest } from '../../shared/apiRequest';

const STATUS_MESSAGES = {
  401: 'Tu sesión venció. Inicia sesión otra vez.',
  403: 'No tienes permiso para realizar esta operación.',
  404: 'El pedido solicitado ya no está disponible.',
  409: 'El pedido cambió mientras lo editabas. Actualiza la vista e inténtalo otra vez.',
  413: 'El archivo supera el tamaño máximo de 1 MB.',
  500: 'El servidor no pudo completar la operación. Inténtalo otra vez.',
};

export class OrdersApiError extends Error {
  constructor(message, status, options = {}) {
    super(message, options);
    this.name = 'OrdersApiError';
    this.status = status;
  }
}

const request = createApiRequest(OrdersApiError, STATUS_MESSAGES);

export const listOrderMaterials = ({ signal, token } = {}) =>
  request('/api/inventory/tipos-vidrio', { signal, token });

export const createOrder = (body, { signal, token } = {}) =>
  request('/api/orders', {
    method: 'POST', body, signal, token,
    validationFallback: 'Revisa el cliente, el material, espesor y las medidas de las piezas.',
  });

export const listOrders = ({ page = 1, limit = 10, estado, cliente, fecha } = {}, { signal, token } = {}) => {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (estado) params.set('estado', estado);
  if (cliente) params.set('cliente', cliente);
  if (fecha) params.set('fecha', fecha);
  return request(`/api/orders?${params}`, { signal, token });
};

export const getOrder = (idPedido, { signal, token, timeoutMs } = {}) =>
  request(`/api/orders/${encodeURIComponent(idPedido)}`, { signal, token, timeoutMs });

export const updateOrder = (idPedido, body, { signal, token } = {}) =>
  request(`/api/orders/${encodeURIComponent(idPedido)}`, {
    method: 'PUT', body, signal, token,
    validationFallback: 'No se pudo actualizar el pedido. Revisa las piezas e inténtalo de nuevo.',
  });

export const cancelOrder = (idPedido, { signal, token } = {}) =>
  request(`/api/orders/${encodeURIComponent(idPedido)}`, { method: 'DELETE', signal, token });


// HU-018: la previsualización y la revalidación no registran nada en la base de datos.
export const previewImport = (file, { signal, token } = {}) => {
  const body = new FormData();
  body.append('archivo', file);
  return request('/api/orders/import/preview', {
    method: 'POST', body, signal, token,
    validationFallback: 'No se pudo leer el archivo. Verifica el formato.',
  });
};

export const validateImport = (body, { signal, token } = {}) =>
  request('/api/orders/import/validate', {
    method: 'POST', body, signal, token,
    validationFallback: 'Revisa el texto de las filas corregidas.',
  });