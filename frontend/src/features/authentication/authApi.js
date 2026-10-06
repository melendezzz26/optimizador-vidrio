// Acceso a la API de autenticación y manejo de la sesión en el navegador.
import { API_URL } from '../../shared/apiUrl';

const SESSION_KEY = 'optimizador.auth';

const CONNECTION_ERROR = 'No se pudo conectar con el servidor. Comprueba que el backend esté en ejecución.';

// Error de la API con el código HTTP, para que quien lo reciba pueda decidir qué hacer.
export class AuthError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'AuthError';
    this.status = status;
  }
}

export function readSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem(SESSION_KEY));
    return session?.access_token && session?.usuario ? session : null;
  } catch {
    return null;
  }
}

export function clearSession() {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // Sin almacenamiento disponible no hay sesión que borrar.
  }
}

// Punto único para que otras features obtengan el token de las peticiones protegidas.
export function getAccessToken() {
  return readSession()?.access_token ?? null;
}

function saveSession(session) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    throw new AuthError('No se pudo guardar la sesión. Habilita el almacenamiento del navegador.');
  }
  return session;
}

function messageFor(status, data) {
  // El backend envía mensajes ya redactados para el usuario en "detail".
  if (typeof data?.detail === 'string') return data.detail;
  if (status === 422) return 'Revisa el usuario y la contraseña ingresados.';
  return 'No se pudo completar la solicitud. Inténtalo otra vez.';
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${API_URL}/api/auth${path}`, options);
  } catch {
    throw new AuthError(CONNECTION_ERROR);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new AuthError(messageFor(response.status, data), response.status);
  if (!data) throw new AuthError('El servidor devolvió una respuesta inesperada.', response.status);
  return data;
}

export async function signIn(username, password) {
  const data = await request('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const user = data.usuario;
  if (!data.access_token || data.token_type !== 'bearer'
    || !user?.id_usuario || !user.username || !user.nombre || !user.rol) {
    throw new AuthError('El servidor devolvió una sesión incompleta.');
  }
  return saveSession({ access_token: data.access_token, token_type: data.token_type, usuario: user });
}

// Confirma con el backend que la sesión guardada sigue vigente y actualiza el rol.
export async function refreshSession() {
  const session = readSession();
  if (!session) throw new AuthError('Debes iniciar sesión.', 401);
  try {
    const current = await request('/me', {
      method: 'GET',
      headers: { Authorization: `Bearer ${session.access_token}` },
    });
    return saveSession({ ...session, usuario: { ...session.usuario, ...current } });
  } catch (error) {
    // 401: el token expiró o la cuenta fue desactivada; la sesión ya no sirve.
    if (error.status === 401) clearSession();
    throw error;
  }
}
