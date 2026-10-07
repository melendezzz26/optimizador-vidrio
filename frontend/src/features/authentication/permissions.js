// Qué opciones de la interfaz se ofrecen a cada rol. Solo decide lo que se
// muestra: el backend valida el permiso en cada petición (matriz de permisos).
export function canManageUsers(user) {
  return user?.rol === 'Administrador';
}

export function canManageOrders(user) {
  return ['Administrador', 'Operario'].includes(user?.rol);
}

export function canViewInventory(user) {
  return ['Administrador', 'Almacenero', 'Operario'].includes(user?.rol);
}

export function canViewResults(user) {
  return ['Administrador', 'Almacenero', 'Operario'].includes(user?.rol);
}

export function canConfigureOptimizer(user) {
  return user?.rol === 'Administrador';
}
