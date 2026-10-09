import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { EmptyState } from '../feedback/EmptyState';
import { LoadingState } from '../feedback/LoadingState';

describe('LoadingState', () => {
  it('anuncia la espera con un texto visible', () => {
    render(<LoadingState>Cargando usuarios…</LoadingState>);
    expect(screen.getByRole('status')).toHaveTextContent('Cargando usuarios…');
  });

  it('usa un texto genérico si no recibe uno', () => {
    render(<LoadingState />);
    expect(screen.getByRole('status')).toHaveTextContent('Cargando…');
  });
});

describe('EmptyState', () => {
  it('explica por qué está vacío y ofrece la acción recibida', () => {
    const onCreate = vi.fn();
    render(
      <EmptyState
        title="Aún no hay usuarios registrados"
        description="Crea el primero para que pueda iniciar sesión."
        action={<button type="button" onClick={onCreate}>Nuevo usuario</button>}
      />,
    );
    const empty = screen.getByRole('status');
    expect(empty).toHaveTextContent('Aún no hay usuarios registrados');
    expect(empty).toHaveTextContent('Crea el primero para que pueda iniciar sesión.');
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo usuario' }));
    expect(onCreate).toHaveBeenCalledTimes(1);
  });

  it('no muestra ninguna acción si no la recibe', () => {
    render(<EmptyState kind="sin-resultados" title="No hay resultados para los filtros seleccionados" />);
    expect(screen.getByRole('status')).toHaveTextContent('No hay resultados');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});