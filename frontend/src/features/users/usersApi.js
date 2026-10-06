// Acceso a la API de gestión de usuarios.
import { API_URL } from '../../shared/apiUrl';
import { getAccessToken } from '../authentication';

const CONNECTION_ERROR = 'No se pudo conectar con el servidor. Comprueba que el backend esté en ejecución.';

// Error de la API con el código HTTP, para que la pantalla decida qué hacer.
export class UsersApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'UsersApiError';
    this.status = status;
  }
}

function messageFor(status, data) {
  // El backend envía mensajes ya redactados para el usuario en "detail".
  if (typeof data?.detail === 'string') return data.detail;
  if (status === 422) return 'Revisa los datos ingresados.';
  return 'No se pudo completar la solicitud. Inténtalo otra vez.';
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { Authorization: `Bearer ${getAccessToken()}` };
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let response;
  try {
    response = await fetch(`${API_URL}/api/users${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new UsersApiError(CONNECTION_ERROR);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new UsersApiError(messageFor(response.status, data), response.status);
  return data;
}

export const listRoles = () => request('/roles');
export const listUsers = () => request('');
export const createUser = (data) => request('', { method: 'POST', body: data });
export const updateUser = (userId, changes) => request(`/${userId}`, { method: 'PATCH', body: changes });
