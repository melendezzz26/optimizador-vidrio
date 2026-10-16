// Solo para pruebas (S1-RBAC): permisos que el backend entrega a cada rol con la
// asignación inicial (backend/app/core/permissions.py). La aplicación nunca
// deduce permisos del nombre del rol; los recibe en login y /api/auth/me.
export const INITIAL_PERMISSIONS = {
  Administrador: [
    'users.view', 'users.manage', 'roles.view', 'roles.manage',
    'inventory.view', 'inventory.manage',
    'orders.view', 'orders.create', 'orders.update', 'orders.cancel',
    'optimization.view', 'optimization.execute', 'optimization.confirm',
  ],
  Almacenero: ['inventory.view', 'inventory.manage', 'optimization.view'],
  Operario: [
    'inventory.view',
    'orders.view', 'orders.create', 'orders.update', 'orders.cancel',
    'optimization.view', 'optimization.execute', 'optimization.confirm',
  ],
};

// Usuario de sesión con los permisos que tendría su rol. Un rol desconocido no tiene permisos.
export const withPermissions = (user) => ({ ...user, permisos: INITIAL_PERMISSIONS[user?.rol] ?? [] });