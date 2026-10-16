import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UsersPage } from '../UsersPage';
import { listRoles, listUsers } from '../usersApi';
import { listPermissions, listRolesWithPermissions, replaceRolePermissions } from '../rolesApi';
import { INITIAL_PERMISSIONS, withPermissions } from '../../authentication/__tests__/permissionFixtures';

vi.mock('../usersApi', () => ({
  listRoles: vi.fn(), listUsers: vi.fn(), createUser: vi.fn(), updateUser: vi.fn(),
}));
vi.mock('../rolesApi', () => ({
  listRolesWithPermissions: vi.fn(), listPermissions: vi.fn(), replaceRolePermissions: vi.fn(),
}));

const CATALOG = [
  { codigo: 'users.view', modulo: 'users', descripcion: 'Ver usuarios y roles disponibles' },
  { codigo: 'roles.view', modulo: 'roles', descripcion: 'Ver roles y sus permisos' },
  { codigo: 'roles.manage', modulo: 'roles', descripcion: 'Cambiar los permisos de un rol' },
  { codigo: 'inventory.view', modulo: 'inventory', descripcion: 'Ver catálogo de vidrio, planchas, retazos e historial' },
  { codigo: 'inventory.manage', modulo: 'inventory', descripcion: 'Registrar, editar y dar de baja tipos, planchas y retazos' },
];
const ROLES = [
  { id_rol: 1, nombre: 'Administrador', permisos: ['inventory.manage', 'inventory.view', 'roles.manage', 'roles.view', 'users.view'] },
  { id_rol: 2, nombre: 'Almacenero', permisos: ['inventory.manage', 'inventory.view'] },
];
const admin = withPermissions({ id_usuario: 1, usuario: 'A74000010', rol: 'Administrador' });
const error = (status, message) => Object.assign(new Error(message), { status });

function renderPage(currentUser = admin, props = {}) {
  return render(<UsersPage currentUser={currentUser} onSessionExpired={vi.fn()} toolbar={null} {...props} />);
}

async function openRolesTab() {
  fireEvent.click(screen.getByRole('tab', { name: 'Roles y permisos' }));
  return screen.findByRole('combobox', { name: 'Rol' });
}

describe('Administración — pestañas y permisos por rol (S1-RBAC)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listRoles.mockResolvedValue([]);
    listUsers.mockResolvedValue([]);
    listRolesWithPermissions.mockResolvedValue(ROLES);
    listPermissions.mockResolvedValue(CATALOG);
  });

  it('muestra Administración con las pestañas Usuarios y Roles y permisos (CA-10)', async () => {
    renderPage();
    expect(screen.getByRole('button', { name: 'Administración', exact: true })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('tablist', { name: 'Administración' })).toBeInTheDocument();
    const tabs = screen.getAllByRole('tab').map((tab) => tab.textContent);
    expect(tabs).toEqual(['Usuarios', 'Roles y permisos']);
    expect(screen.getByRole('tab', { name: 'Usuarios' })).toHaveAttribute('aria-selected', 'true');
    expect(await screen.findByRole('heading', { name: 'Usuarios registrados' })).toBeInTheDocument();
  });

  it('las flechas del teclado cambian de pestaña', async () => {
    renderPage();
    const usersTab = screen.getByRole('tab', { name: 'Usuarios' });
    fireEvent.keyDown(usersTab, { key: 'ArrowRight' });
    expect(screen.getByRole('tab', { name: 'Roles y permisos' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Roles y permisos' })).toHaveFocus();
    expect(await screen.findByRole('combobox', { name: 'Rol' })).toBeInTheDocument();
  });

  it('carga roles y catálogo, y marca los permisos del rol elegido', async () => {
    renderPage();
    const select = await openRolesTab();
    expect(screen.getByRole('checkbox', { name: /Ver usuarios y roles disponibles/ })).toBeChecked();

    fireEvent.change(select, { target: { value: '2' } });
    expect(screen.getByRole('checkbox', { name: /Ver usuarios y roles disponibles/ })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: /Registrar, editar y dar de baja/ })).toBeChecked();
    expect(screen.getByRole('group', { name: 'Inventario' })).toBeInTheDocument();
  });

  it('guarda el conjunto completo marcado y muestra confirmación', async () => {
    replaceRolePermissions.mockResolvedValue({ id_rol: 2, nombre: 'Almacenero', permisos: ['inventory.view'] });
    renderPage();
    fireEvent.change(await openRolesTab(), { target: { value: '2' } });

    const save = screen.getByRole('button', { name: 'Guardar cambios' });
    expect(save).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox', { name: /Registrar, editar y dar de baja/ }));
    expect(save).toBeEnabled();
    fireEvent.click(save);

    await waitFor(() => expect(replaceRolePermissions).toHaveBeenCalledWith(2, ['inventory.view']));
    expect(await screen.findByText('Se guardaron los permisos de Almacenero.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeDisabled();
  });

  it('Descartar vuelve a los permisos guardados sin llamar a la API', async () => {
    renderPage();
    fireEvent.change(await openRolesTab(), { target: { value: '2' } });
    const checkbox = screen.getByRole('checkbox', { name: /Registrar, editar y dar de baja/ });
    fireEvent.click(checkbox);
    expect(checkbox).not.toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: 'Descartar' }));
    expect(checkbox).toBeChecked();
    expect(replaceRolePermissions).not.toHaveBeenCalled();
  });

  it('roles.view y roles.manage aparecen bloqueados para el Administrador (RN-05)', async () => {
    renderPage();
    await openRolesTab();
    for (const name of [/Ver roles y sus permisos/, /Cambiar los permisos de un rol/]) {
      const checkbox = screen.getByRole('checkbox', { name });
      expect(checkbox).toBeChecked();
      expect(checkbox).toBeDisabled();
      expect(checkbox).toHaveAccessibleDescription('El Administrador siempre conserva este permiso.');
    }
    expect(screen.getByRole('checkbox', { name: /Ver usuarios y roles disponibles/ })).toBeEnabled();
  });

  it('un 409 del backend se muestra sin perder lo marcado', async () => {
    replaceRolePermissions.mockRejectedValue(error(409, 'El Administrador debe conservar los permisos para ver y gestionar roles.'));
    renderPage();
    await openRolesTab();
    fireEvent.click(screen.getByRole('checkbox', { name: /Ver usuarios y roles disponibles/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('No se guardaron los cambios');
    expect(alert).toHaveTextContent('El Administrador debe conservar');
    expect(screen.getByRole('checkbox', { name: /Ver usuarios y roles disponibles/ })).not.toBeChecked();
  });

  it('al cambiar los permisos del propio rol se vuelve a pedir la sesión', async () => {
    const onPermissionsChanged = vi.fn();
    replaceRolePermissions.mockResolvedValue({ ...ROLES[0], permisos: ['roles.manage', 'roles.view'] });
    renderPage(admin, { onPermissionsChanged });
    await openRolesTab();
    fireEvent.click(screen.getByRole('checkbox', { name: /Ver usuarios y roles disponibles/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(onPermissionsChanged).toHaveBeenCalledOnce());
  });

  it('un 401 al cargar roles cierra la sesión', async () => {
    const onSessionExpired = vi.fn();
    listRolesWithPermissions.mockRejectedValue(error(401, 'Tu sesión venció. Inicia sesión otra vez.'));
    render(<UsersPage currentUser={admin} onSessionExpired={onSessionExpired} toolbar={null} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Roles y permisos' }));
    expect(await screen.findByText('Tu sesión venció. Inicia sesión otra vez.')).toBeInTheDocument();
    expect(onSessionExpired).toHaveBeenCalled();
  });
});

describe('Administración — lo que se ve depende de los permisos de la sesión', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listRoles.mockResolvedValue([]);
    listUsers.mockResolvedValue([{ id_usuario: 2, usuario: 'F70303030', nombres: 'Carlos', apellidos: 'Pérez', id_rol: 3, rol: 'Operario', estado: true }]);
    listRolesWithPermissions.mockResolvedValue(ROLES);
    listPermissions.mockResolvedValue(CATALOG);
  });

  it('con solo roles.view: solo la pestaña de roles, en modo consulta y sin pedir usuarios', async () => {
    renderPage({ id_usuario: 9, rol: 'Auditor', permisos: ['roles.view'] });
    expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual(['Roles y permisos']);
    await screen.findByRole('combobox', { name: 'Rol' });
    expect(listUsers).not.toHaveBeenCalled();
    expect(screen.getByText('Solo consulta')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Guardar cambios' })).not.toBeInTheDocument();
    for (const checkbox of screen.getAllByRole('checkbox')) expect(checkbox).toBeDisabled();
  });

  it('con users.view sin users.manage: lista de usuarios sin acciones ni alta', async () => {
    renderPage({ id_usuario: 9, rol: 'Auditor', permisos: ['users.view'] });
    expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual(['Usuarios']);
    const table = await screen.findByRole('table');
    expect(within(table).queryByRole('columnheader', { name: 'Acciones' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Nuevo usuario' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Editar a/ })).not.toBeInTheDocument();
  });

  it('con los permisos iniciales del Administrador se puede gestionar todo', async () => {
    expect(INITIAL_PERMISSIONS.Administrador).toContain('roles.manage');
    renderPage();
    expect(await screen.findByRole('button', { name: 'Nuevo usuario' })).toBeInTheDocument();
    await openRolesTab();
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeInTheDocument();
  });
});