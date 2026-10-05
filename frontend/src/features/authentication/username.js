// Formato del usuario de acceso, igual que en el backend: una letra y 8 dígitos.
// Esta comprobación solo mejora el mensaje al usuario; la regla que decide es la del backend.
const USERNAME_PATTERN = /^[A-Z][0-9]{8}$/;

export const USERNAME_HINT = 'Una letra seguida de 8 dígitos. Ejemplo: F71234567.';

export function normalizeUsername(value) {
  return value.trim().toUpperCase();
}

export function isValidUsername(value) {
  return USERNAME_PATTERN.test(value);
}
