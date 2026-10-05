import './SessionBar.css';

// Muestra quién tiene la sesión iniciada y permite cerrarla.
export function SessionBar({ user, onSignOut }) {
  return (
    <header className="session-bar">
      <p className="session-bar-name">{user.nombre}</p>
      <dl className="session-bar-details">
        <div>
          <dt>Usuario</dt>
          <dd>{user.username}</dd>
        </div>
        <div>
          <dt>Rol</dt>
          <dd>{user.rol}</dd>
        </div>
      </dl>
      <button type="button" className="session-bar-sign-out" onClick={onSignOut}>
        Cerrar sesión
      </button>
    </header>
  );
}
