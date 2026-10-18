import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UsersPage } from '../UsersPage';
import { listRoles, listUsers } from '../usersApi';
import { withPermissions } from '../../authentication/__tests__/permissionFixtures';

vi.mock('../usersApi', () => ({
  listRoles: vi.fn(),
  listUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
}));

const admin = { id_usuario: 1, usuario: 'A74000010', nombres: 'Admin', apellidos: 'NewGlass', id_rol: 1, rol: 'Administrador', estado: true };
const carlos = { id_usuario: 2, usuario: 'F70303030', nombres: 'Carlos', apellidos: 'Pérez', id_rol: 3, rol: 'Operario', estado: true };
const ana = { id_usuario: 3, usuario: 'A00000001', nombres: 'Ana', apellidos: 'Núñez', id_rol: 2, rol: 'Almacenero', estado: false };

const roles = [
  { id_rol: 1, nombre: 'Administrador' },
  { id_rol: 2, nombre: 'Almacenero' },
  { id_rol: 3, nombre: 'Operario' },
];

async function renderLoadedPage() {
  render(<UsersPage currentUser={withPermissions(admin)} onSessionExpired={vi.fn()} toolbar={null} />);
  await screen.findByText('F70303030');
}

describe('UsersPage — búsqueda y filtros (HU-003 T04)', () => {
  beforeEach(() => {
    listRoles.mockResolvedValue(roles);
    listUsers.mockResolvedValue([admin, carlos, ana]);
  });

  it('muestra los controles y el total de usuarios', async () => {
    await renderLoadedPage();
    expect(screen.getByLabelText('Buscar')).toBeInTheDocument();
    expect(screen.getByLabelText('Rol')).toBeInTheDocument();
    expect(screen.getByLabelText('Estado')).toBeInTheDocument();
    expect(screen.getByText('Mostrando 3 de 3 usuarios')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Limpiar filtros' })).not.toBeInTheDocument();
  });

  it('busca por nombre sin importar tildes', async () => {
    await renderLoadedPage();
    fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'perez' } });
    expect(screen.getByText('F70303030')).toBeInTheDocument();
    expect(screen.queryByText('A00000001')).not.toBeInTheDocument();
    expect(screen.getByText('Mostrando 1 de 3 usuarios')).toBeInTheDocument();
  });

  it('combina rol y estado', async () => {
    await renderLoadedPage();
    fireEvent.change(screen.getByLabelText('Rol'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'inactive' } });
    expect(screen.getByText('A00000001')).toBeInTheDocument();
    expect(screen.queryByText('F70303030')).not.toBeInTheDocument();
    expect(screen.getByText('Mostrando 1 de 3 usuarios')).toBeInTheDocument();
  });

  it('sin coincidencias muestra el estado vacío y Limpiar filtros recupera el listado', async () => {
    await renderLoadedPage();
    fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'carlos' } });
    fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'inactive' } });
    expect(screen.getByText('No hay usuarios que coincidan con la búsqueda.')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Limpiar filtros' }));
    expect(screen.getByText('Mostrando 3 de 3 usuarios')).toBeInTheDocument();
    expect(screen.getByLabelText('Buscar')).toHaveValue('');
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('sin usuarios registrados no muestra los filtros', async () => {
    listUsers.mockResolvedValue([]);
    render(<UsersPage currentUser={withPermissions(admin)} onSessionExpired={vi.fn()} toolbar={null} />);
    expect(await screen.findByText('Aún no hay usuarios registrados')).toBeInTheDocument();
    expect(screen.queryByLabelText('Buscar')).not.toBeInTheDocument();
  });
});