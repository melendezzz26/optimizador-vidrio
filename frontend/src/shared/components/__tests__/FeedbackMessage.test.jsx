import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FeedbackMessage } from '../feedback/FeedbackMessage';

describe('FeedbackMessage', () => {
  it('anuncia un error de inmediato y lo identifica con texto', () => {
    render(<FeedbackMessage variant="error">No se pudo guardar el usuario.</FeedbackMessage>);
    const message = screen.getByRole('alert');
    expect(message).toHaveTextContent('Error');
    expect(message).toHaveTextContent('No se pudo guardar el usuario.');
  });

  it.each([
    ['success', 'Operación completada'],
    ['warning', 'Advertencia'],
    ['info', 'Información'],
  ])('muestra la variante %s como estado con su título visible', (variant, label) => {
    render(<FeedbackMessage variant={variant}>Detalle del mensaje.</FeedbackMessage>);
    expect(screen.getByRole('status')).toHaveTextContent(label);
  });

  it('usa el título recibido en lugar del título por defecto', () => {
    render(<FeedbackMessage variant="success" title="Usuario creado" />);
    expect(screen.getByRole('status')).toHaveTextContent('Usuario creado');
    expect(screen.getByRole('status')).not.toHaveTextContent('Operación completada');
  });
});