import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ConfirmDialog } from '../feedback/ConfirmDialog';

function renderDialog(props = {}) {
  const handlers = { onConfirm: vi.fn(), onCancel: vi.fn() };
  const view = render(
    <ConfirmDialog
      open
      title="¿Desactivar a Carlos Pérez?"
      confirmLabel="Desactivar"
      {...handlers}
      {...props}
    >
      No podrá iniciar sesión hasta que lo vuelvas a activar.
    </ConfirmDialog>,
  );
  return { ...view, ...handlers };
}

describe('ConfirmDialog', () => {
  it('no dibuja nada mientras está cerrado', () => {
    const { container } = renderDialog({ open: false });
    expect(container).toBeEmptyDOMElement();
  });

  it('se anuncia con su pregunta y su consecuencia, y empieza en Cancelar', () => {
    renderDialog();
    const dialog = screen.getByRole('alertdialog', { name: '¿Desactivar a Carlos Pérez?' });
    expect(dialog).toHaveAccessibleDescription('No podrá iniciar sesión hasta que lo vuelvas a activar.');
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus();
  });

  it('confirma con su botón y cancela con Escape', () => {
    const { onConfirm, onCancel } = renderDialog();
    fireEvent.click(screen.getByRole('button', { name: 'Desactivar' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(screen.getByRole('alertdialog'), { key: 'Escape' });
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('mantiene el foco dentro del diálogo al usar Tab', () => {
    renderDialog();
    const confirm = screen.getByRole('button', { name: 'Desactivar' });
    confirm.focus();
    fireEvent.keyDown(screen.getByRole('alertdialog'), { key: 'Tab' });
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus();
  });

  it('devuelve el foco al botón que lo abrió al cerrarse', () => {
    const { rerender } = render(<button type="button">Desactivar usuario</button>);
    const trigger = screen.getByRole('button', { name: 'Desactivar usuario' });
    trigger.focus();
    const dialog = (open) => (
      <>
        <button type="button">Desactivar usuario</button>
        <ConfirmDialog open={open} title="¿Desactivar?" confirmLabel="Desactivar"
          onConfirm={() => {}} onCancel={() => {}}>Consecuencia.</ConfirmDialog>
      </>
    );
    rerender(dialog(true));
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus();
    rerender(dialog(false));
    expect(screen.getByRole('button', { name: 'Desactivar usuario' })).toHaveFocus();
  });

  it('bloquea los botones mientras se confirma', () => {
    renderDialog({ isConfirming: true });
    expect(screen.getByRole('button', { name: 'Desactivar' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled();
  });
});