import { useCallback, useEffect, useId, useState } from 'react';
import { AppShell } from '../../shared/components/AppShell';
import { PageCard } from '../../shared/components/PageLayout';
import { UserForm } from './UserForm';
import { UsersTable } from './UsersTable';
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
  const [editingUser, setEditingUser] = useState(null);
  const [pendingUserId, setPendingUserId] = useState(null);
  const [notice, setNotice] = useState('');
  const [tableError, setTableError] = useState('');
  const listTitleId = useId();

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
    setNotice('');
    setTableError('');
    try {
      if (editingUser) {
        const changes = { nombres: values.nombres, apellidos: values.apellidos };
        if (Number(values.id_rol) !== editingUser.id_rol) changes.id_rol = Number(values.id_rol);
        if (values.password) changes.password = values.password;
        const updated = await updateUser(editingUser.id_usuario, changes);
        replaceUser(updated);
        setEditingUser(null);
        setNotice(`Se guardaron los cambios de ${updated.usuario}.`);
      } else {
        const created = await createUser({
          nombres: values.nombres,
          apellidos: values.apellidos,
          dni: values.dni,
          password: values.password,
          id_rol: Number(values.id_rol),
        });
        setUsers((current) => [...current, created]);
        setNotice(`Usuario registrado. Su usuario de acceso es ${created.usuario}.`);
      }
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async function handleToggleStatus(user) {
    setNotice('');
    setTableError('');
    setPendingUserId(user.id_usuario);
    try {
      const updated = await updateUser(user.id_usuario, { estado: !user.estado });
      replaceUser(updated);
      setNotice(`${updated.usuario} quedó ${updated.estado ? 'activo' : 'inactivo'}.`);
    } catch (error) {
      setTableError(handleApiError(error).message);
    } finally {
      setPendingUserId(null);
    }
  }

  function startEditing(user) {
    setNotice('');
    setTableError('');
    setEditingUser(user);
  }

  return (
    <AppShell activeItem="roles">
      {toolbar}

      {isLoading && <PageCard><p role="status">Cargando usuarios...</p></PageCard>}
      {loadError && <PageCard><p className="users-error" role="alert">{loadError}</p></PageCard>}

      {!isLoading && !loadError && (
        <>
          <UserForm
            key={editingUser ? editingUser.id_usuario : 'new'}
            roles={roles}
            editingUser={editingUser}
            isOwnAccount={editingUser?.id_usuario === currentUser.id_usuario}
            onSubmit={handleSubmit}
            onCancel={() => setEditingUser(null)}
          />

          <PageCard as="section" className="users-list" aria-labelledby={listTitleId}>
            <h2 id={listTitleId}>Usuarios registrados</h2>
            {notice && <p className="users-notice" role="status">{notice}</p>}
            {tableError && <p className="users-error" role="alert">{tableError}</p>}
            <UsersTable
              users={users}
              currentUserId={currentUser.id_usuario}
              pendingUserId={pendingUserId}
              onEdit={startEditing}
              onToggleStatus={handleToggleStatus}
            />
          </PageCard>
        </>
      )}
    </AppShell>
  );
}
