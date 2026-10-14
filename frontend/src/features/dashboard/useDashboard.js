import { useEffect, useState } from 'react';
import { loadDashboardSource } from './dashboardApi';
import {
  createDashboardBlocks, DashboardDataError, getDashboardActions, getDashboardSources,
  getDashboardStatus, isDashboardSourceEmpty, transformDashboardSource,
} from './dashboardModel';

const NOOP = () => {};
const matches = (snapshot, context) => snapshot && ['userId', 'role', 'token', 'version'].every(key => snapshot[key] === context[key]);
const safeError = error => error instanceof DashboardDataError ? error.message
  : error.status === 403 ? 'No tienes permiso para consultar esta información.'
    : 'No se pudo cargar esta información. Inténtalo otra vez.';

export function useDashboard({ user, token, onSessionExpired = NOOP }) {
  const [version, setVersion] = useState(0);
  const [snapshot, setSnapshot] = useState(null);
  const role = user?.rol;
  const userId = user?.id_usuario;
  const context = { userId, role, token, version };
  const blocks = matches(snapshot, context) ? snapshot.blocks : createDashboardBlocks(user);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const currentContext = { userId, role, token, version };
    const currentUser = { rol: role };
    const initialBlocks = createDashboardBlocks(currentUser);
    const sources = getDashboardSources(currentUser);
    const publish = (source, block) => {
      if (!active) return;
      setSnapshot(previous => ({ ...currentContext, blocks: {
        ...(matches(previous, currentContext) ? previous.blocks : initialBlocks), [source]: block,
      } }));
    };
    for (const source of sources) {
      loadDashboardSource(source, { signal: controller.signal, token })
        .then(response => {
          if (!active) return;
          const data = transformDashboardSource(source, response);
          publish(source, { status: isDashboardSourceEmpty(source, data) ? 'empty' : 'success', data, error: '' });
        })
        .catch(error => {
          if (!active || error.name === 'AbortError') return;
          if (error.status === 401) {
            active = false;
            controller.abort();
            setSnapshot({ ...currentContext, blocks: Object.fromEntries(sources.map(id => [id, {
              status: 'error', data: null, error: 'Tu sesión venció. Inicia sesión otra vez.',
            }])) });
            onSessionExpired();
            return;
          }
          publish(source, { status: 'error', data: null, error: safeError(error) });
        });
    }
    return () => { active = false; controller.abort(); };
  }, [userId, role, token, version, onSessionExpired]);

  return { blocks, status: getDashboardStatus(blocks), actions: getDashboardActions(user), refresh: () => setVersion(value => value + 1) };
}
