import { EmptyState } from '../../shared/components/feedback';
// Tabla de usuarios. No muestra el DNI (SPEC-HU-003, RN-09).
export function UsersTable({ users, currentUserId, pendingUserId, onEdit, onToggleStatus }) {
  if (users.length === 0) {
    return (
      <EmptyState
        title="Aún no hay usuarios registrados"
        description="Registra el primero con el formulario de esta página."
      />
    );
  }

  return (
    <div className="users-table-scroll">
      <table className="users-table">
        <caption className="users-visually-hidden">Usuarios registrados</caption>
        <thead>
          <tr>
            <th scope="col">Usuario</th>
            <th scope="col">Nombre</th>
            <th scope="col">Rol</th>
            <th scope="col">Estado</th>
            <th scope="col">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const isOwnAccount = user.id_usuario === currentUserId;
            const fullName = `${user.nombres} ${user.apellidos}`;
            return (
              <tr key={user.id_usuario}>
                <th scope="row">{user.usuario}</th>
                <td>{fullName}</td>
                <td>{user.rol}</td>
                <td>
                  <span className={user.estado ? 'users-badge users-badge--active' : 'users-badge'}>
                    {user.estado ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td>
                  <div className="users-row-actions">
                    <button type="button" className="ng-button users-row-button"
                      onClick={() => onEdit(user)} aria-label={`Editar a ${fullName}`}>
                      Editar
                    </button>
                    {isOwnAccount ? (
                      <span className="users-hint">Tu cuenta</span>
                    ) : (
                      <button type="button" className="ng-button users-row-button"
                        onClick={() => onToggleStatus(user)}
                        disabled={pendingUserId === user.id_usuario}
                        aria-label={`${user.estado ? 'Desactivar' : 'Activar'} a ${fullName}`}>
                        {user.estado ? 'Desactivar' : 'Activar'}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
