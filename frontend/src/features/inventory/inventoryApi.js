// Acceso a la API de inventario.
import { API_URL } from '../../shared/apiUrl';
import { getAccessToken } from '../authentication';

const CONNECTION_ERROR = 'No se pudo conectar con el servidor. Comprueba que el backend esté en ejecución.';

// Error de la API con el código HTTP, para que la pantalla pueda decidir qué mostrar.
export class InventoryApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message);
    this.name = 'InventoryApiError';
    this.status = status;
    this.data = data;
  }
}

function messageFor(status, data) {
  if (typeof data?.detail === 'string') return data.detail;
  if (status === 401) return 'Tu sesión no es válida o ha expirado.';
  if (status === 403) return 'No tienes permisos para realizar esta operación.';
  if (status === 409) return 'La operación entra en conflicto con los datos existentes.';
  if (status === 422) return 'Revisa los datos ingresados.';
  return 'No se pudo completar la solicitud. Inténtalo otra vez.';
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { Authorization: `Bearer ${getAccessToken()}` };
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let response;
  try {
    response = await fetch(`${API_URL}/api/inventory${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new InventoryApiError(CONNECTION_ERROR);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new InventoryApiError(messageFor(response.status, data), response.status, data);
  }
  return data;
}

export const getTiposVidrio = () => request('/tipos-vidrio');
export const getPlanchas = () => request('/planchas');
export const createPlancha = (payload) => request('/planchas', { method: 'POST', body: payload });
export const updatePlancha = (idPlancha, payload) => request(`/planchas/${idPlancha}`, {
  method: 'PATCH',
  body: payload,
});
export const getRetazos = () => request('/retazos');
export const createRetazo = (payload) => request('/retazos', { method: 'POST', body: payload });
export const updateRetazo = (idRetazo, payload) => request(`/retazos/${idRetazo}`, {
  method: 'PATCH',
  body: payload,
});
