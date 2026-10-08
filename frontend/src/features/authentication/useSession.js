import { useCallback, useEffect, useState } from 'react';
import { clearSession, readSession, refreshSession, signIn as requestSignIn } from './authApi';

// Estado de la sesión para la aplicación: quién está conectado y cómo entrar o salir.
export function useSession() {
  const [session, setSession] = useState(null);
  // Si hay una sesión guardada, primero se confirma con el backend.
  const [isChecking, setIsChecking] = useState(() => Boolean(readSession()));
  const [notice, setNotice] = useState('');

  useEffect(() => {
    if (!readSession()) return undefined;
    let active = true;
    refreshSession()
      .then((current) => { if (active) setSession(current); })
      .catch((error) => { if (active) setNotice(error.message); })
      .finally(() => { if (active) setIsChecking(false); });
    return () => { active = false; };
  }, []);

  const signIn = useCallback(async (username, password) => {
    setNotice('');
    setSession(await requestSignIn(username, password));
  }, []);

  const signOut = useCallback((message) => {
  clearSession();
  setSession(null);
  setNotice(
    typeof message === 'string'
      ? message
      : 'Sesión cerrada.'
  );
  }, []);

  return { session, isChecking, notice, signIn, signOut };
}
