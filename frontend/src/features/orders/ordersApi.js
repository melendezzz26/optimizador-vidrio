import { API_URL } from '../../shared/apiUrl';
import { getAccessToken } from '../authentication';

async function request(path, { method = 'GET', body, signal } = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method, signal,
      headers: { Authorization: `Bearer ${getAccessToken()}`,
        ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('No se pudo conectar con el servidor. Revisa la conexión y vuelve a intentar.', { cause: error });
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const fallback = response.status === 422 ? 'Revisa el material, espesor y las medidas de las piezas.'
      : 'No se pudo completar la solicitud. Inténtalo otra vez.';
    throw new Error(typeof data?.detail === 'string' ? data.detail : fallback);
  }
  if (!data || (method === 'POST' && (response.status !== 201 || !Number.isInteger(data.id_pedido)))) {
    throw new Error('El servidor devolvió una respuesta inesperada.');
  }
  return data;
}

export const listOrderMaterials = (signal) => request('/api/inventory/tipos-vidrio', { signal });
export const createOrder = (body) => request('/api/orders', { method: 'POST', body });
