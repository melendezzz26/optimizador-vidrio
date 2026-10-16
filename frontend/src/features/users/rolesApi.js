// Acceso a la API de roles y permisos (S1-RBAC), con el transporte compartido.
import { createApiRequest } from '../../shared/apiRequest';

const STATUS_MESSAGES = {
  401: 'Tu sesión venció. Inicia sesión otra vez.',
  403: 'No tienes permiso para realizar esta acción.',
  404: 'El rol ya no existe. Actualiza la página.',
  409: 'El Administrador debe conservar los permisos para ver y gestionar roles.',
  500: 'El servidor no pudo completar la operación. Inténtalo otra vez.',
};

export class RolesApiError extends Error {
  constructor(message, status, options = {}) {
    super(message, options);
    this.name = 'RolesApiError';
    this.status = status;
  }
}

const request = createApiRequest(RolesApiError, STATUS_MESSAGES);

export const listRolesWithPermissions = () => request('/api/roles');
export const listPermissions = () => request('/api/permissions');
export const replaceRolePermissions = (roleId, permisos) => request(`/api/roles/${roleId}/permissions`, {
  method: 'PUT',
  body: { permisos },
  validationFallback: 'Hay permisos que no existen en el catálogo.',
});