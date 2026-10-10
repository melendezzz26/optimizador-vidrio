import { API_URL } from '../../shared/apiUrl';
import { getAccessToken } from '../authentication';

async function request(path, { method = 'GET', body, signal, token, validationFallback } = {}) {
  const accessToken = token ?? getAccessToken();
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method, signal,
      headers: { ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('No se pudo conectar con el servidor. Revisa la conexión y vuelve a intentar.', { cause: error });
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const fallback = response.status === 422 ? validationFallback ?? 'Revisa el material, espesor y las medidas de las piezas.'
      : 'No se pudo completar la solicitud. Inténtalo otra vez.';
    throw new Error(typeof data?.detail === 'string' ? data.detail : fallback);
  }
  if (!data || (method === 'POST' && (response.status !== 201 || !Number.isInteger(data.id_pedido)))) {
    throw new Error('El servidor devolvió una respuesta inesperada.');
  }
  return data;
}

export const listOrderMaterials = ({ signal, token } = {}) =>
  request('/api/inventory/tipos-vidrio', { signal, token });
export const createOrder = (body, { token } = {}) =>
  request('/api/orders/', {
    method: 'POST', body, token,
    validationFallback: 'No se pudo registrar el pedido. Revisa las piezas e inténtalo de nuevo.',
  });
