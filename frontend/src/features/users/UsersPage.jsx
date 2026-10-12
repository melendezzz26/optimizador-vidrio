import { useCallback, useEffect, useId, useState } from 'react';
import { ShieldCheck, UserPlus } from 'lucide-react';
import { AppShell } from '../../shared/components/AppShell';
import { PageCard, PageHeader } from '../../shared/components/PageLayout';
import { useManagementView } from '../../shared/hooks/useManagementView';
import { ConfirmDialog, EmptyState, FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import { UserForm } from './UserForm';
import { UsersFilters } from './UsersFilters';
import { UsersTable } from './UsersTable';
import { EMPTY_USER_FILTERS, filterUsers } from './userFilters';
import { createUser, listRoles, listUsers, updateUser } from './usersApi';
import './users.css';

// Pantalla de gestión de usuarios dentro de la base visual compartida.
// currentUser es la cuenta con la sesión iniciada; toolbar, lo que la
// aplicación quiera mostrar sobre el contenido (sesión y cambio de sección).
export function UsersPage({ currentUser, onSessionExpired, toolbar }) {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [pendingUserId, setPendingUserId] = useState(null);
  const [tableError, setTableError] = useState('');
  const [userToDeactivate, setUserToDeactivate] = useState(null);
  const [filters, setFilters] = useState(EMPTY_USER_FILTERS);
  const listTitleId = useId();
  const pageTitleId = useId();

  // Listado primero y formulario solo bajo acción (HU-003 T05, patrón de TA-034 T02).
  const {
    editingItem: editingUser, isListVisible, isFormOpen,
    feedback, setFeedback, openCreate, openEdit, backToList,
  } = useManagementView();

  // La lista visible se calcula en cada render; no se guarda en el estado.
  const visibleUsers = filterUsers(users, filters);

  // 401: la sesión expiró o la cuenta fue desactivada; se vuelve al inicio de sesión.
  const handleApiError = useCallback((error) => {
    if (error.status === 401) onSessionExpired();
    return error;
  }, [onSessionExpired]);

  useEffect(() => {
    let active = true;
    Promise.all([listRoles(), listUsers()])
      .then(([loadedRoles, loadedUsers]) => {
        if (!active) return;
        setRoles(loadedRoles);
        setUsers(loadedUsers);
      })
      .catch((error) => { if (active) setLoadError(handleApiError(error).message); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [handleApiError]);

  function replaceUser(updated) {
    setUsers((current) => current.map((user) => (user.id_usuario === updated.id_usuario ? updated : user)));
  }

  async function handleSubmit(values) {
    setTableError('');
    try {
      if (editingUser) {
        const changes = { nombres: values.nombres, apellidos: values.apellidos };
        if (Number(values.id_rol) !== editingUser.id_rol) changes.id_rol = Number(values.id_rol);
        if (values.password) changes.password = values.password;
        const updated = await updateUser(editingUser.id_usuario, changes);
        replaceUser(updated);
        backToList({ variant: 'success', message: `Se guardaron los cambios de ${updated.usuario}.` });
      } else {
        const created = await createUser({
          nombres: values.nombres,
          apellidos: values.apellidos,
          dni: values.dni,
          password: values.password,
          id_rol: Number(values.id_rol),
        });
        setUsers((current) => [...current, created]);
        backToList({ variant: 'success', message: `Usuario registrado. Su usuario de acceso es ${created.usuario}.` });
      }
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async function changeStatus(user) {
    setFeedback(null);
    setTableError('');
    setPendingUserId(user.id_usuario);
    try {
      const updated = await updateUser(user.id_usuario, { estado: !user.estado });
      replaceUser(updated);
      setFeedback({ variant: 'success', message: `${updated.usuario} quedó ${updated.estado ? 'activo' : 'inactivo'}.` });
    } catch (error) {
      setTableError(handleApiError(error).message);
    } finally {
      setPendingUserId(null);
    }
  }

  // Desactivar quita el acceso, por eso se confirma antes; activar no lo necesita.
  function handleToggleStatus(user) {
    if (user.estado) {
      setFeedback(null);
      setTableError('');
      setUserToDeactivate(user);
    } else {
      changeStatus(user);
    }
  }

  async function confirmDeactivation() {
    await changeStatus(userToDeactivate);
    setUserToDeactivate(null);
  }

  function startCreating() {
    setTableError('');
    openCreate();
  }

  function startEditing(user) {
    setTableError('');
    openEdit(user);
  }

  return (
    <AppShell activeItem="roles" user={currentUser}>
      {toolbar}

      <PageHeader context="Panel de roles" title="Gestión de usuarios" titleId={pageTitleId}
        icon={ShieldCheck}
        description="Busca usuarios, asígnales un rol y activa o desactiva su acceso." />

      {isLoading && <PageCard><LoadingState>Cargando usuarios…</LoadingState></PageCard>}
      {loadError && (
        <PageCard>
          <FeedbackMessage variant="error" title="No se pudieron cargar los usuarios">{loadError}</FeedbackMessage>
        </PageCard>
      )}

      {!isLoading && !loadError && isFormOpen && (
        <UserForm
          key={editingUser ? editingUser.id_usuario : 'new'}
          roles={roles}
          editingUser={editingUser}
          isOwnAccount={editingUser?.id_usuario === currentUser.id_usuario}
          onSubmit={handleSubmit}
          onCancel={() => backToList()}
        />
      )}

      {!isLoading && !loadError && isListVisible && (
        <PageCard as="section" className="users-list" aria-labelledby={listTitleId}>
          <div className="users-list-header">
            <h2 id={listTitleId}>Usuarios registrados</h2>
            <button className="ng-button ng-button--primary" type="button" onClick={startCreating}>
              <UserPlus size={18} aria-hidden="true" />
              Nuevo usuario
            </button>
          </div>
          {feedback && <FeedbackMessage variant={feedback.variant}>{feedback.message}</FeedbackMessage>}
          {tableError && (
            <FeedbackMessage variant="error" title="No se pudo cambiar el estado">{tableError}</FeedbackMessage>
          )}
          {users.length === 0 ? (
            <EmptyState
              title="Aún no hay usuarios registrados"
              description="Usa «Nuevo usuario» para registrar el primero."
            />
          ) : (
            <>
              <UsersFilters
                filters={filters}
                roles={roles}
                onChange={setFilters}
                onClear={() => setFilters(EMPTY_USER_FILTERS)}
              />
              <p className="users-count" role="status">
                Mostrando {visibleUsers.length} de {users.length} usuarios
              </p>
              {visibleUsers.length === 0 ? (
                <EmptyState
                  kind="sin-resultados"
                  title="No hay usuarios que coincidan con la búsqueda."
                  description="Cambia la búsqueda o los filtros, o usa «Limpiar filtros» para ver a todos."
                />
              ) : (
                <UsersTable
                  users={visibleUsers}
                  currentUserId={currentUser.id_usuario}
                  pendingUserId={pendingUserId}
                  onEdit={startEditing}
                  onToggleStatus={handleToggleStatus}
                />
              )}
            </>
          )}
        </PageCard>
      )}

      <ConfirmDialog
        open={userToDeactivate !== null}
        title={userToDeactivate ? `¿Desactivar a ${userToDeactivate.nombres} ${userToDeactivate.apellidos}?` : ''}
        confirmLabel="Desactivar"
        onConfirm={confirmDeactivation}
        onCancel={() => setUserToDeactivate(null)}
        isConfirming={userToDeactivate !== null && pendingUserId === userToDeactivate.id_usuario}
      >
        <p>No podrá iniciar sesión hasta que lo vuelvas a activar. Sus datos se conservan.</p>
      </ConfirmDialog>
    </AppShell>
  );
}