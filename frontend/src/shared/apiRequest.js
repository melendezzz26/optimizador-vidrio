import { API_URL } from './apiUrl';
import { getAccessToken } from '../features/authentication/authApi';

// Transporte compartido por Orders y Optimization; cada feature conserva sus mensajes.
export function createApiRequest(ApiError, statusMessages) {
  return async function request(path, { method = 'GET', body, signal, token, validationFallback, timeoutMs } = {}) {
    const accessToken = token ?? getAccessToken();
    const controller = timeoutMs ? new AbortController() : null;
    let timedOut = false;
    const abort = () => controller?.abort();
    if (signal?.aborted) abort();
    signal?.addEventListener('abort', abort, { once: true });
    const timer = timeoutMs ? setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs) : null;
    try {
      const response = await fetch(`${API_URL}${path}`, {
        method, signal: controller?.signal ?? signal,
        headers: {
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          ...(body ? { 'Content-Type': 'application/json' } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await response.json().catch(error => {
        if (error.name === 'AbortError') throw error;
        return null;
      });
      if (!response.ok) {
        const message = response.status === 422
          ? (typeof data?.detail === 'string' ? data.detail : validationFallback ?? 'Revisa los datos del pedido e inténtalo otra vez.')
          : statusMessages[response.status] ?? 'No se pudo completar la solicitud. Inténtalo otra vez.';
        throw new ApiError(message, response.status);
      }
      if (!data) throw new ApiError('El servidor devolvió una respuesta inesperada.', response.status);
      return data;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (error.name === 'AbortError' && !timedOut) throw error;
      throw new ApiError(timedOut
        ? 'El servidor tardó demasiado en responder. Comprueba el estado e inténtalo otra vez.'
        : 'No se pudo conectar con el servidor. Revisa la conexión e inténtalo otra vez.', 0, { cause: error });
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener('abort', abort);
    }
  };
}
