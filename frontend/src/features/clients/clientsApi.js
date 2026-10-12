import { API_URL } from '../../shared/apiUrl';
import { getAccessToken } from '../authentication';

async function request({ method = 'GET', body, params, signal, token } = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}/api/clients${params ? `?${params}` : ''}`, {
      method, signal,
      headers: { Authorization: `Bearer ${token ?? getAccessToken()}`,
        ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('No se pudo conectar con el servidor. Revisa la conexión y vuelve a intentar.', { cause: error });
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const fallback = {
      401: 'Tu sesión ha expirado. Vuelve a iniciar sesión.',
      403: 'No tienes permiso para gestionar clientes.',
      409: 'Ya existe un cliente con ese tipo y número de documento. Búscalo para seleccionarlo.',
      422: 'Revisa los datos del cliente e inténtalo de nuevo.',
    }[response.status] || 'No se pudo completar la operación de clientes. Inténtalo otra vez.';
    throw new Error(response.status === 422 && typeof data?.detail === 'string' ? data.detail : fallback);
  }
  if (method === 'GET' ? !Array.isArray(data) : response.status !== 201 || !Number.isInteger(data?.id_cliente)) {
    throw new Error('El servidor devolvió una respuesta inesperada. Inténtalo otra vez.');
  }
  return data;
}

export const searchClients = (value, mode, options) => request({
  ...options, params: new URLSearchParams({ [mode === 'document' ? 'document' : 'query']: value.trim() }),
});
export const createClient = (body, options) => request({ ...options, method: 'POST', body });
