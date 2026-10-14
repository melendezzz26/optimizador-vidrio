import { useState } from 'react';
import {
  LoginForm,
  SessionBar,
  canManageOrders,
  canExecuteOptimization,
  canManageUsers,
  canViewInventory,
  useSession,
} from './features/authentication';
import { InventoryPage } from './features/inventory/InventoryPage';
import { UsersPage } from './features/users';
import GestionPedidos from './features/orders/GestionPedidos';
import { OptimizationPage } from './features/optimization';

import { NavigationContext } from './shared/components/NavigationContext';
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

  const showOrdersOption = canManageOrders(session.usuario);
  const showInventoryOption = canViewInventory(session.usuario);
  const showUsersOption = canManageUsers(session.usuario);
  const allowedViews = [
    showOrdersOption && 'orders',
    canExecuteOptimization(session.usuario) && 'optimization',
    showInventoryOption && 'inventory',
    showUsersOption && 'users',
  ].filter(Boolean);
  const fallbackView = allowedViews[0];
  const currentView = allowedViews.includes(view) ? view : fallbackView;

  const toolbar = <SessionBar user={session.usuario} onSignOut={signOut} />;

  let page;
  if (currentView === 'users') {
    page = <UsersPage currentUser={session.usuario} onSessionExpired={signOut} toolbar={toolbar} />;
  } else if (currentView === 'optimization') {
    page = <OptimizationPage user={session.usuario} token={session.token || session.access_token} onSessionExpired={signOut} toolbar={toolbar} />;
  } else if (currentView === 'inventory') {
    page = <InventoryPage onSessionExpired={signOut} toolbar={toolbar} user={session.usuario} />;
  } else page = <GestionPedidos
    token={session.token || session.access_token}
    user={session.usuario}
    onSessionExpired={signOut}
    toolbar={toolbar}
  />;

  return <NavigationContext.Provider value={{ onNavigate: setView, availableViews: allowedViews }}>{page}</NavigationContext.Provider>;
}

export default App;
