// Qué opciones de la interfaz se ofrecen según los permisos de la sesión
// (S1-RBAC). Los permisos llegan del backend en login y /api/auth/me; aquí no
// hay ninguna lista de roles. Solo decide lo que se muestra: el backend valida
// el permiso en cada petición.
export function hasPermission(user, code) {
  return Array.isArray(user?.permisos) && user.permisos.includes(code);
}

const hasAny = (user, codes) => codes.some((code) => hasPermission(user, code));

// Inicio muestra datos de inventario y de pedidos: basta con poder ver uno de los dos.
export const canViewDashboard = (user) => hasAny(user, ['inventory.view', 'orders.view']);

// Módulo de pedidos y clientes.
export const canManageOrders = (user) => hasPermission(user, 'orders.view');

export const canExecuteOptimization = (user) => hasPermission(user, 'optimization.execute');
export const canViewResults = (user) => hasPermission(user, 'optimization.view');
// D-01 de la SPEC: aún no existe un permiso para configurar el optimizador.
export const canConfigureOptimizer = (user) => hasPermission(user, 'optimization.configure');

export const canViewInventory = (user) => hasPermission(user, 'inventory.view');
export const canManagePlanchas = (user) => hasPermission(user, 'inventory.manage');
export const canManageRetazos = (user) => hasPermission(user, 'inventory.manage');

// Administración: pestañas Usuarios y Roles y permisos.
export const canViewUsers = (user) => hasPermission(user, 'users.view');
export const canManageUsers = (user) => hasPermission(user, 'users.manage');
export const canViewRoles = (user) => hasPermission(user, 'roles.view');
export const canManageRoles = (user) => hasPermission(user, 'roles.manage');
export const canViewAdministration = (user) => canViewUsers(user) || canViewRoles(user);