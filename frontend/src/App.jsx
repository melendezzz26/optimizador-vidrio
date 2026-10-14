import { useState } from 'react';
import {
  LoginForm,
  SessionBar,
  canExecuteOptimization,
  canManageOrders,
  canManagePlanchas,
  canManageRetazos,
  canManageUsers,
  canViewInventory,
  useSession,
} from './features/authentication';
import { DashboardPage } from './features/dashboard/DashboardPage';
import { InventoryPage } from './features/inventory/InventoryPage';
import { OptimizationPage } from './features/optimization';
import { UsersPage } from './features/users';
import GestionPedidos from './features/orders/GestionPedidos';
import NuevoPedido from './features/orders/NuevoPedido';
import { NavigationContext } from './shared/components/NavigationContext';
import './App.css';

function App() {
  const { session, isChecking, notice, signIn, signOut } = useSession();
  const [view, setView] = useState('dashboard');
  const [navigationRequest, setNavigationRequest] = useState(null);

  if (isChecking) {
    return <p className="app-status" role="status">Comprobando la sesión…</p>;
  }

  if (!session) {
    return <LoginForm onSignIn={signIn} notice={notice} />;
  }

  const usuario = session.usuario;
  const showOrdersOption = canManageOrders(usuario);
  const showInventoryOption = canViewInventory(usuario);
  const showOptimizationOption = canExecuteOptimization(usuario);
  const showUsersOption = canManageUsers(usuario);
  const showPlanchaRegistration = canManagePlanchas(usuario);
  const showRetazoRegistration = canManageRetazos(usuario);
  const showDashboardOption = showOrdersOption || showInventoryOption || showOptimizationOption;
  const allowedViews = [
    showDashboardOption && 'dashboard',
    showOrdersOption && 'orders',
    showOrdersOption && 'new-order',
    showOptimizationOption && 'optimization',
    showInventoryOption && 'inventory',
    showPlanchaRegistration && 'register-plancha',
    showRetazoRegistration && 'register-retazo',
    showUsersOption && 'users',
  ].filter(Boolean);
  const fallbackView = allowedViews[0];
  const currentView = allowedViews.includes(view) ? view : fallbackView;

  const toolbar = <SessionBar user={usuario} onSignOut={signOut} />;
  const navigate = (nextView, request = null) => {
    setNavigationRequest(request ? { target: nextView, ...request } : null);
    setView(nextView);
  };

  let page;
  if (currentView === 'dashboard') {
    page = <DashboardPage
      token={session.token || session.access_token}
      user={usuario}
      canAccessOrders={showOrdersOption}
      canAccessInventory={showInventoryOption}
      canAccessOptimization={showOptimizationOption}
      canRegisterSheets={showPlanchaRegistration}
      canRegisterOffcuts={showRetazoRegistration}
      onSessionExpired={signOut}
      toolbar={toolbar}
    />;
  } else if (currentView === 'new-order') {
    page = <NuevoPedido
      token={session.token || session.access_token}
      user={usuario}
      toolbar={toolbar}
    />;
  } else if (currentView === 'optimization') {
    page = <OptimizationPage
      user={usuario}
      token={session.token || session.access_token}
      onSessionExpired={signOut}
      toolbar={toolbar}
    />;
  } else if (currentView === 'users') {
    page = <UsersPage currentUser={usuario} onSessionExpired={signOut} toolbar={toolbar} />;
  } else if (['inventory', 'register-plancha', 'register-retazo'].includes(currentView)) {
    page = <InventoryPage
      onSessionExpired={signOut}
      toolbar={toolbar}
      user={usuario}
      initialAction={currentView === 'register-plancha' ? 'plancha' : currentView === 'register-retazo' ? 'retazo' : null}
    />;
  } else {
    page = <GestionPedidos
      token={session.token || session.access_token}
      user={usuario}
      onSessionExpired={signOut}
      toolbar={toolbar}
      requestedOrder={navigationRequest?.target === 'orders' ? navigationRequest.order : null}
    />;
  }

  return <NavigationContext.Provider value={{ onNavigate: navigate, availableViews: allowedViews }}>{page}</NavigationContext.Provider>;
}

export default App;
