// Dirección del backend, compartida por las features que llaman a la API.
export const API_URL = (import.meta.env?.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
