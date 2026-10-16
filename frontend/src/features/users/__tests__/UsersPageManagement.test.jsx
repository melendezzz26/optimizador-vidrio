import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UsersPage } from '../UsersPage';
import { createUser, listRoles, listUsers, updateUser } from '../usersApi';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures';

vi.mock('../usersApi', () => ({
  listRoles: vi.fn(),
  listUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
}));

const admin = { id_usuario: 1, usuario: 'A74000010', nombres: 'Admin', apellidos: 'NewGlass', dni: '74000010', id_rol: 1, rol: 'Administrador', estado: true };
const carlos = { id_usuario: 2, usuario: 'F70303030', nombres: 'Carlos', apellidos: 'Pérez', dni: '70303030', id_rol: 3, rol: 'Operario', estado: true };
const roles = [{ id_rol: 1, nombre: 'Administrador' }, { id_rol: 3, nombre: 'Operario' }];

async function renderLoadedPage() {
  render(<UsersPage currentUser={withPermissions(admin)} onSessionExpired={vi.fn()} toolbar={null} />);
  await screen.findByText('F70303030');
}

function fillNewUser() {
  fireEvent.change(screen.getByLabelText('Nombres *'), { target: { value: 'Luis' } });
  fireEvent.change(screen.getByLabelText('Apellidos *'), { target: { value: 'Ramos' } });
  fireEvent.change(screen.getByLabelText('DNI *'), { target: { value: '12345678' } });
  fireEvent.change(screen.getByLabelText('Contraseña *'), { target: { value: 'clave-segura' } });
  fireEvent.change(screen.getByLabelText('Rol *'), { target: { value: '3' } });
}

describe('UsersPage — listado primero y formulario bajo acción (HU-003 T05)', () => {
  beforeEach(() => {
    listRoles.mockResolvedValue(roles);
    listUsers.mockResolvedValue([admin, carlos]);
  });

  it('al entrar muestra el listado y no el formulario', async () => {
    await renderLoadedPage();
    expect(screen.getByRole('heading', { name: 'Usuarios registrados' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nuevo usuario' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Nombres *')).not.toBeInTheDocument();
  });

  it('Nuevo usuario abre el formulario en lugar del listado y Cancelar vuelve sin perder los filtros', async () => {
    await renderLoadedPage();
    fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'carlos' } });

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo usuario' }));
    expect(screen.getByRole('heading', { name: 'Nuevo usuario' })).toHaveFocus();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(screen.queryByLabelText('Nombres *')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Buscar')).toHaveValue('carlos');
    expect(screen.getByText('Mostrando 1 de 2 usuarios')).toBeInTheDocument();
  });

  it('al registrar vuelve al listado con el mensaje de éxito', async () => {
    createUser.mockResolvedValue({ id_usuario: 3, usuario: 'L12345678', nombres: 'Luis', apellidos: 'Ramos', id_rol: 3, rol: 'Operario', estado: true });
    await renderLoadedPage();
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo usuario' }));
    fillNewUser();
    fireEvent.click(screen.getByRole('button', { name: 'Registrar usuario' }));

    expect(await screen.findByText('Usuario registrado. Su usuario de acceso es L12345678.')).toBeInTheDocument();
    expect(screen.queryByLabelText('Nombres *')).not.toBeInTheDocument();
    expect(screen.getByText('L12345678')).toBeInTheDocument();
  });

  it('un usuario duplicado mantiene el formulario abierto con el error junto al DNI', async () => {
    createUser.mockRejectedValue(Object.assign(new Error('Ya existe un usuario con ese DNI.'), { status: 409 }));
    await renderLoadedPage();
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo usuario' }));
    fillNewUser();
    fireEvent.click(screen.getByRole('button', { name: 'Registrar usuario' }));

    expect(await screen.findByText('Ya existe un usuario con ese DNI.')).toBeInTheDocument();
    expect(screen.getByLabelText('DNI *')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('Editar abre el formulario con los datos actuales y al guardar vuelve al listado', async () => {
    updateUser.mockResolvedValue({ ...carlos, nombres: 'Carlos Alberto' });
    await renderLoadedPage();
    fireEvent.click(screen.getByRole('button', { name: 'Editar a Carlos Pérez' }));

    expect(screen.getByRole('heading', { name: 'Editar usuario F70303030' })).toBeInTheDocument();
    expect(screen.getByLabelText('Nombres *')).toHaveValue('Carlos');
    fireEvent.change(screen.getByLabelText('Nombres *'), { target: { value: 'Carlos Alberto' } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));

    expect(await screen.findByText('Se guardaron los cambios de F70303030.')).toBeInTheDocument();
    expect(updateUser).toHaveBeenCalledWith(2, { nombres: 'Carlos Alberto', apellidos: 'Pérez' });
    expect(screen.getByText('Carlos Alberto Pérez')).toBeInTheDocument();
  });
});