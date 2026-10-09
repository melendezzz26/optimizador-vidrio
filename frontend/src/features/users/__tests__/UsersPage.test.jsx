import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UsersPage } from '../UsersPage';
import { listRoles, listUsers, updateUser } from '../usersApi';

vi.mock('../usersApi', () => ({
  listRoles: vi.fn(),
  listUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
}));

const admin = { id_usuario: 1, usuario: 'A74000010', rol: 'Administrador' };
const carlos = {
  id_usuario: 2, usuario: 'F70303030', nombres: 'Carlos', apellidos: 'Pérez',
  id_rol: 3, rol: 'Operario', estado: true,
};

function renderPage() {
  return render(<UsersPage currentUser={admin} onSessionExpired={vi.fn()} toolbar={null} />);
}

describe('UsersPage — feedback compartido (TA-034)', () => {
  beforeEach(() => {
    listRoles.mockResolvedValue([{ id_rol: 3, nombre: 'Operario' }]);
    listUsers.mockResolvedValue([carlos]);
  });

  it('muestra la carga y luego el listado', async () => {
    renderPage();
    expect(screen.getByRole('status')).toHaveTextContent('Cargando usuarios…');
    expect(await screen.findByText('F70303030')).toBeInTheDocument();
  });

  it('muestra el estado vacío cuando no hay usuarios', async () => {
    listUsers.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText('Aún no hay usuarios registrados')).toBeInTheDocument();
  });

  it('muestra el error de carga como alerta', async () => {
    listUsers.mockRejectedValue(Object.assign(new Error('No se pudo conectar con el servidor.'), { status: 0 }));
    renderPage();
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('No se pudieron cargar los usuarios');
    expect(alert).toHaveTextContent('No se pudo conectar con el servidor.');
  });

  it('pide confirmación antes de desactivar y no cambia nada si se cancela', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Desactivar a Carlos Pérez' }));
    expect(screen.getByRole('alertdialog', { name: '¿Desactivar a Carlos Pérez?' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(updateUser).not.toHaveBeenCalled();
  });

  it('desactiva solo después de confirmar y muestra el resultado', async () => {
    updateUser.mockResolvedValue({ ...carlos, estado: false });
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Desactivar a Carlos Pérez' }));
    fireEvent.click(screen.getByRole('button', { name: 'Desactivar' }));
    expect(await screen.findByText('F70303030 quedó inactivo.')).toBeInTheDocument();
    expect(updateUser).toHaveBeenCalledWith(2, { estado: false });
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });
});