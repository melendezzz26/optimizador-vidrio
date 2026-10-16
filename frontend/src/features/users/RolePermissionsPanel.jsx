import { useCallback, useEffect, useId, useState } from 'react';
import { PageCard } from '../../shared/components/PageLayout';
import { FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import { listPermissions, listRolesWithPermissions, replaceRolePermissions } from './rolesApi';

// Nombres en español de cada módulo del catálogo de permisos.
const MODULE_LABELS = {
  users: 'Usuarios',
  roles: 'Roles y permisos',
  inventory: 'Inventario',
  orders: 'Pedidos y clientes',
  optimization: 'Optimización',
};

// RN-05: el backend responde 409 si se quitan; aquí solo se muestran bloqueados.
const ADMINISTRATOR_ROLE = 'Administrador';
const PROTECTED_FOR_ADMINISTRATOR = ['roles.view', 'roles.manage'];

function groupByModule(permissions) {
  const groups = new Map();
  for (const permission of permissions) {
    if (!groups.has(permission.modulo)) groups.set(permission.modulo, []);
    groups.get(permission.modulo).push(permission);
  }
  return [...groups.entries()];
}

const sameSet = (left, right) => left.length === right.length && left.every((code) => right.includes(code));

// Pestaña "Roles y permisos": elegir un rol y marcar o desmarcar sus permisos.
// canManage decide si se puede guardar; sin él, la vista es de solo lectura.
export function RolePermissionsPanel({ currentUser, canManage, onApiError, onOwnRoleChanged }) {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [selectedRoleId, setSelectedRoleId] = useState(null);
  const [draft, setDraft] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const selectId = useId();

  const selectedRole = roles.find((role) => role.id_rol === selectedRoleId) ?? null;
  const hasChanges = selectedRole !== null && !sameSet(draft, selectedRole.permisos);

  const reportError = useCallback((error) => onApiError(error).message, [onApiError]);

  useEffect(() => {
    let active = true;
    Promise.all([listRolesWithPermissions(), listPermissions()])
      .then(([loadedRoles, loadedPermissions]) => {
        if (!active) return;
        setRoles(loadedRoles);
        setPermissions(loadedPermissions);
        if (loadedRoles.length > 0) {
          setSelectedRoleId(loadedRoles[0].id_rol);
          setDraft(loadedRoles[0].permisos);
        }
      })
      .catch((error) => { if (active) setLoadError(reportError(error)); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [reportError]);

  function selectRole(roleId) {
    const role = roles.find((item) => item.id_rol === roleId);
    setSelectedRoleId(roleId);
    setDraft(role ? role.permisos : []);
    setFeedback(null);
  }

  function togglePermission(code) {
    setFeedback(null);
    setDraft((current) => (current.includes(code)
      ? current.filter((item) => item !== code)
      : [...current, code]));
  }

  function isLocked(code) {
    return selectedRole?.nombre === ADMINISTRATOR_ROLE && PROTECTED_FOR_ADMINISTRATOR.includes(code);
  }

  async function save() {
    setIsSaving(true);
    setFeedback(null);
    try {
      const updated = await replaceRolePermissions(selectedRole.id_rol, draft);
      setRoles((current) => current.map((role) => (role.id_rol === updated.id_rol ? updated : role)));
      setDraft(updated.permisos);
      setFeedback({ variant: 'success', message: `Se guardaron los permisos de ${updated.nombre}.` });
      // Si cambió el rol de la sesión, se piden de nuevo sus permisos para actualizar el menú.
      if (updated.nombre === currentUser?.rol) onOwnRoleChanged?.();
    } catch (error) {
      setFeedback({ variant: 'error', message: reportError(error) });
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) return <PageCard><LoadingState>Cargando roles y permisos…</LoadingState></PageCard>;
  if (loadError) {
    return (
      <PageCard>
        <FeedbackMessage variant="error" title="No se pudieron cargar los roles">{loadError}</FeedbackMessage>
      </PageCard>
    );
  }

  return (
    <PageCard as="section" className="roles-panel" aria-label="Permisos por rol">
      <div className="ng-field roles-select">
        <label htmlFor={selectId}>Rol</label>
        <select id={selectId} className="ng-control" value={selectedRoleId ?? ''}
          disabled={isSaving} onChange={(event) => selectRole(Number(event.target.value))}>
          {roles.map((role) => <option key={role.id_rol} value={role.id_rol}>{role.nombre}</option>)}
        </select>
      </div>

      {!canManage && (
        <FeedbackMessage variant="info" title="Solo consulta">
          Puedes ver los permisos de cada rol, pero no cambiarlos.
        </FeedbackMessage>
      )}
      {feedback && (
        <FeedbackMessage variant={feedback.variant} title={feedback.variant === 'error' ? 'No se guardaron los cambios' : undefined}>
          {feedback.message}
        </FeedbackMessage>
      )}

      {groupByModule(permissions).map(([module, items]) => (
        <fieldset key={module} className="ng-form-section roles-group">
          <legend>{MODULE_LABELS[module] ?? module}</legend>
          <ul className="roles-list">
            {items.map((permission) => {
              const locked = isLocked(permission.codigo);
              const hintId = `${selectId}-${permission.codigo}-hint`;
              return (
                <li key={permission.codigo}>
                  <label className="roles-option">
                    <input
                      type="checkbox"
                      checked={draft.includes(permission.codigo)}
                      disabled={!canManage || isSaving || locked}
                      aria-describedby={locked ? hintId : undefined}
                      onChange={() => togglePermission(permission.codigo)}
                    />
                    <span>
                      {permission.descripcion}
                      <code className="roles-code">{permission.codigo}</code>
                    </span>
                  </label>
                  {locked && (
                    <p id={hintId} className="users-hint">El Administrador siempre conserva este permiso.</p>
                  )}
                </li>
              );
            })}
          </ul>
        </fieldset>
      ))}

      {canManage && (
        <div className="ng-action-bar">
          <button type="button" className="ng-button" disabled={!hasChanges || isSaving}
            onClick={() => selectRole(selectedRoleId)}>
            Descartar
          </button>
          <button type="button" className="ng-button ng-button--primary" disabled={!hasChanges || isSaving}
            aria-busy={isSaving} onClick={save}>
            {isSaving ? 'Guardando…' : 'Guardar cambios'}
          </button>
        </div>
      )}
    </PageCard>
  );
}