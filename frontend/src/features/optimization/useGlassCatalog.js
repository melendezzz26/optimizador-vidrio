import { useEffect, useState } from 'react';
import { listOrderMaterials } from '../orders/ordersApi';

export function useGlassCatalog({ token, enabled, onSessionExpired }) {
  const [catalog, setCatalog] = useState({ token, status: 'loading', materials: [] });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!enabled) return undefined;
    const controller = new AbortController();
    listOrderMaterials({ token, signal: controller.signal }).then(materials => {
      if (!Array.isArray(materials)) throw new Error('Invalid glass catalog');
      if (!controller.signal.aborted) setCatalog({ token, status: 'ready', materials });
    }).catch(error => {
      if (controller.signal.aborted) return;
      if (error.status === 401) onSessionExpired?.();
      setCatalog({ token, status: 'error', materials: [] });
    });
    return () => controller.abort();
  }, [token, enabled, onSessionExpired, attempt]);
  return {
    ...(catalog.token === token ? catalog : { status: 'loading', materials: [] }),
    retry: () => { setCatalog({ token, status: 'loading', materials: [] }); setAttempt(n => n + 1); },
  };
}

export function glassGroups(groups, catalog) {
  return groups.map(group => {
    const material = catalog.materials.find(m => String(m.id_tipo_vidrio) === String(group.materialId));
    const knownName = group.name && !/^Material #/.test(group.name) ? group.name : null;
    const name = material?.nombre ?? knownName ?? (catalog.status === 'ready'
      ? `Material #${group.materialId}` : catalog.status === 'error' ? 'Vidrio sin identificar' : 'Consultando vidrio…');
    return { ...group, name, containers: group.containers.map(c => ({ ...c, material_name: name })) };
  });
}
