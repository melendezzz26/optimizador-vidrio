import { useCallback, useState } from 'react';
import {
  LoginForm,
  SessionBar,
  canManageOrders,
  canViewResults,
  canViewAdministration,
  canViewInventory,
  canViewDashboard,
  useSession,
} from './features/authentication';
import { InventoryPage } from './features/inventory/InventoryPage';
import { UsersPage } from './features/users';
import GestionPedidos from './features/orders/GestionPedidos';
import { OptimizationPage } from './features/optimization';
import { DashboardPage } from './features/dashboard';

import { NavigationContext } from './shared/components/NavigationContext';
import './App.css';

function App() {
  
 const { session, isChecking, notice, signIn, signOut, refresh } = useSession();
  const [view, setView] = useState('dashboard');
  const handleSignOut = useCallback(message => {
    setView('dashboard');
    signOut(message);
  }, [signOut]);

  async function handleSignIn(username, password) {
    await signIn(username, password);
    setView('dashboard');
  }
  
  if (isChecking) {
    return <p className="app-status" role="status">Comprobando la sesión…</p>;
  }

  if (!session) {
    return <LoginForm onSignIn={handleSignIn} notice={notice} />;
  }

  const showOrdersOption = canManageOrders(session.usuario);
  const showInventoryOption = canViewInventory(session.usuario);
  const showUsersOption = canViewAdministration(session.usuario);
  const allowedViews = [
    canViewDashboard(session.usuario) && 'dashboard',
    showOrdersOption && 'orders',
    canViewResults(session.usuario) && 'optimization',
    showInventoryOption && 'inventory',
    showUsersOption && 'users',
  ].filter(Boolean);
  const fallbackView = allowedViews[0];
  const currentView = allowedViews.includes(view) ? view : fallbackView;

  const toolbar = <SessionBar user={session.usuario} onSignOut={handleSignOut} />;

  if (!allowedViews.length) return <>{toolbar}<p role="alert">Tu rol no tiene módulos habilitados.</p></>;

  let page;
  if (currentView === 'dashboard') {
    page = <DashboardPage user={session.usuario} token={session.token || session.access_token} onSessionExpired={handleSignOut} toolbar={toolbar} />;
  } else if (currentView === 'users') {
    page = <UsersPage currentUser={session.usuario} onSessionExpired={handleSignOut} toolbar={toolbar} onPermissionsChanged={refresh} />;
  } else if (currentView === 'optimization') {
    page = <OptimizationPage user={session.usuario} token={session.token || session.access_token} onSessionExpired={handleSignOut} toolbar={toolbar} />;
  } else if (currentView === 'inventory') {
    page = <InventoryPage onSessionExpired={handleSignOut} toolbar={toolbar} user={session.usuario} />;
  } else page = <GestionPedidos
    token={session.token || session.access_token}
    user={session.usuario}
    onSessionExpired={handleSignOut}
    toolbar={toolbar}
  />;

  return <NavigationContext.Provider value={{ onNavigate: setView, availableViews: allowedViews }}>{page}</NavigationContext.Provider>;
}

export default App;
