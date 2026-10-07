import { useState } from 'react';
import { LoginForm, SessionBar, canManageUsers, useSession } from './features/authentication';
import { UsersPage } from './features/users';
import NuevoPedido from './pages/NuevoPedido';
import './App.css';

function App() {
  const { session, isChecking, notice, signIn, signOut } = useSession();
  const [view, setView] = useState('orders');

  if (isChecking) {
    return <p className="app-status" role="status">Comprobando la sesión…</p>;
  }

  if (!session) {
    return <LoginForm onSignIn={signIn} notice={notice} />;
  }

  // La gestión de usuarios solo se ofrece a quien puede usarla; el backend
  // valida el permiso de todos modos.
  const showUsersOption = canManageUsers(session.usuario);
  const currentView = showUsersOption ? view : 'orders';

  const toolbar = (
    <div className="app-toolbar">
      <SessionBar user={session.usuario} onSignOut={signOut} />
      {showUsersOption && (
        <nav className="app-nav" aria-label="Secciones">
          <button type="button" className="app-nav-button"
            aria-current={currentView === 'orders' ? 'page' : undefined}
            onClick={() => setView('orders')}>
            Registro de pedidos
          </button>
          <button type="button" className="app-nav-button"
            aria-current={currentView === 'users' ? 'page' : undefined}
            onClick={() => setView('users')}>
            Panel de roles
          </button>
        </nav>
      )}
    </div>
  );

  if (currentView === 'users') {
    return <UsersPage currentUser={session.usuario} onSessionExpired={signOut} toolbar={toolbar} />;
  }

  return (
    <div className="app-container">
      {toolbar}
      <NuevoPedido />
    </div>
  );
}

export default App;
