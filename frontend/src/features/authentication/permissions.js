// Qué opciones de la interfaz se ofrecen a cada rol. Solo decide lo que se
// muestra: el backend valida el permiso en cada petición (matriz de permisos).
export function canManageUsers(user) {
  return user?.rol === 'Administrador';
}
