import { useId } from 'react';
import { hasActiveFilters } from './userFilters';

// Búsqueda y filtros del listado de usuarios (HU-003 T04).
// Solo dibuja los controles; qué usuarios se ven lo decide filterUsers (userFilters.js).
export function UsersFilters({ filters, roles, onChange, onClear }) {
  const id = useId();

  // Devuelve el manejador de un control: copia los filtros y cambia solo ese campo.
  function changeField(field) {
    return (event) => onChange({ ...filters, [field]: event.target.value });
  }

  return (
    <>
      <fieldset className="users-filters">
        <legend className="users-visually-hidden">Buscar y filtrar usuarios</legend>

        <div className="ng-field">
          <label htmlFor={`${id}-query`}>Buscar</label>
          <input id={`${id}-query`} className="ng-control" type="search" autoComplete="off"
            placeholder="Usuario, nombres o apellidos"
            value={filters.query} onChange={changeField('query')} />
        </div>

        <div className="ng-field">
          <label htmlFor={`${id}-role`}>Rol</label>
          <select id={`${id}-role`} className="ng-control"
            value={filters.roleId} onChange={changeField('roleId')}>
            <option value="">Todos</option>
            {roles.map((role) => (
              <option key={role.id_rol} value={String(role.id_rol)}>{role.nombre}</option>
            ))}
          </select>
        </div>

        <div className="ng-field">
          <label htmlFor={`${id}-status`}>Estado</label>
          <select id={`${id}-status`} className="ng-control"
            value={filters.status} onChange={changeField('status')}>
            <option value="">Todos</option>
            <option value="active">Activo</option>
            <option value="inactive">Inactivo</option>
          </select>
        </div>
      </fieldset>

      {hasActiveFilters(filters) && (
        <div className="users-filter-actions">
          <button className="ng-button" type="button" onClick={onClear}>Limpiar filtros</button>
        </div>
      )}
    </>
  );
}