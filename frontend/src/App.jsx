import { LoginForm, SessionBar, useSession } from './features/authentication';
import NuevoPedido from './pages/NuevoPedido';
import './App.css';

function App() {
  const { session, isChecking, notice, signIn, signOut } = useSession();

  if (isChecking) {
    return <p className="app-status" role="status">Comprobando la sesión…</p>;
  }

  if (!session) {
    return <LoginForm onSignIn={signIn} notice={notice} />;
  }

  return (
    <div className="app-container">
      <SessionBar user={session.usuario} onSignOut={signOut} />
      <NuevoPedido />
    </div>
  );
}

export default App;
