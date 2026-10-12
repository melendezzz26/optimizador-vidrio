// Búsqueda y filtros de la gestión de usuarios (HU-003 T04).
// Funciones puras: reciben la lista ya cargada y devuelven la parte visible.
// No cambian datos ni deciden permisos; eso lo sigue haciendo el backend.

export const EMPTY_USER_FILTERS = { query: '', roleId: '', status: '' };

// Quita tildes y mayúsculas para que "perez" encuentre "Pérez".
export function normalizeText(text) {
  return String(text ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

export function filterUsers(users, filters) {
  const words = normalizeText(filters.query).split(/\s+/).filter(Boolean);

  return users.filter((user) => {
    const searchable = normalizeText(`${user.usuario} ${user.nombres} ${user.apellidos}`);
    const matchesQuery = words.every((word) => searchable.includes(word));
    const matchesRole = !filters.roleId || user.id_rol === Number(filters.roleId);
    const matchesStatus = !filters.status || user.estado === (filters.status === 'active');
    return matchesQuery && matchesRole && matchesStatus;
  });
}

export function hasActiveFilters(filters) {
  return Object.values(filters).some((value) => String(value).trim() !== '');
}