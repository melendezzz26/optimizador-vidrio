import { useState } from 'react';
import {
  LoginForm,
  SessionBar,
  canManageOrders,
  canManageUsers,
  canViewInventory,
  useSession,
} from './features/authentication';
import { InventoryPage } from './features/inventory/InventoryPage';
import { UsersPage } from './features/users';
import CustomPieceEditor from './features/orders/CustomPieceEditor';
import GestionPedidos from './features/orders/GestionPedidos';

import './App.css';

function App() {
  
  const { session, isChecking, notice, signIn, signOut } = useSession();
  const [view, setView] = useState('orders');
  
  if (window.location.pathname === '/editor-pieza') {
    return <CustomPieceEditor />;
  }



  if (isChecking) {
    return <p className="app-status" role="status">Comprobando la sesión…</p>;
  }

  if (!session) {
    return <LoginForm onSignIn={signIn} notice={notice} />;
  }

  const showOrdersOption = canManageOrders(session.usuario);
  const showInventoryOption = canViewInventory(session.usuario);
  const showUsersOption = canManageUsers(session.usuario);
  const allowedViews = [
    showOrdersOption && 'orders',
    showInventoryOption && 'inventory',
    showUsersOption && 'users',
  ].filter(Boolean);
  const fallbackView = allowedViews[0];
  const currentView = allowedViews.includes(view) ? view : fallbackView;

  const toolbar = (
    <div className="app-toolbar">
      <SessionBar user={session.usuario} onSignOut={signOut} />
      <nav className="app-nav" aria-label="Secciones">
          {showOrdersOption && <button type="button" className="app-nav-button"
            aria-current={currentView === 'orders' ? 'page' : undefined}
            onClick={() => setView('orders')}>
            Registro de pedidos
          </button>}
          {showInventoryOption && <button type="button" className="app-nav-button"
            aria-current={currentView === 'inventory' ? 'page' : undefined}
            onClick={() => setView('inventory')}>
            Gestión de inventario
          </button>}
          {showUsersOption && <button type="button" className="app-nav-button"
            aria-current={currentView === 'users' ? 'page' : undefined}
            onClick={() => setView('users')}>
            Panel de roles
          </button>}
      </nav>
    </div>
  );

  if (currentView === 'users') {
    return <UsersPage currentUser={session.usuario} onSessionExpired={signOut} toolbar={toolbar} />;
  }

  if (currentView === 'inventory') {
    return <InventoryPage onSessionExpired={signOut} toolbar={toolbar} user={session.usuario} />;
  }

  return <GestionPedidos
    token={session.token || session.access_token}
    user={session.usuario}
    onSessionExpired={signOut}
    toolbar={toolbar}
  />;
}

export default App;
