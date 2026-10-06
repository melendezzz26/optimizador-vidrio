// Comprobaciones del formulario para avisar junto a cada campo antes de enviar.
// Solo mejoran los mensajes: las reglas que deciden son las del backend.
const DNI_PATTERN = /^[0-9]{8}$/;
const MIN_PASSWORD_LENGTH = 8;

export const EMPTY_FORM = { nombres: '', apellidos: '', dni: '', password: '', id_rol: '' };

export function validateUserForm(values, { isEditing }) {
  const errors = {};
  if (!values.nombres.trim()) errors.nombres = 'Ingresa los nombres.';
  if (!values.apellidos.trim()) errors.apellidos = 'Ingresa los apellidos.';
  if (!isEditing && !DNI_PATTERN.test(values.dni)) errors.dni = 'El DNI debe tener exactamente 8 dígitos.';
  if (!values.id_rol) errors.id_rol = 'Selecciona un rol.';

  const passwordIsRequired = !isEditing;
  if (passwordIsRequired && !values.password) {
    errors.password = 'Ingresa una contraseña.';
  } else if (values.password && values.password.length < MIN_PASSWORD_LENGTH) {
    errors.password = `La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`;
  }
  return errors;
}
