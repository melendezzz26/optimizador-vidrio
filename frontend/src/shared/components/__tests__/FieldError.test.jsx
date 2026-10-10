import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FieldError } from '../feedback/FieldError';

describe('FieldError', () => {
  it('queda asociado al campo como su descripción accesible', () => {
    render(
      <>
        <label htmlFor="dni">DNI</label>
        <input id="dni" aria-invalid="true" aria-describedby="dni-error" />
        <FieldError id="dni-error">El DNI debe tener exactamente 8 dígitos.</FieldError>
      </>,
    );
    expect(screen.getByLabelText('DNI')).toHaveAccessibleDescription('El DNI debe tener exactamente 8 dígitos.');
  });

  it('no dibuja nada cuando no hay error', () => {
    const { container } = render(<FieldError id="dni-error" />);
    expect(container).toBeEmptyDOMElement();
  });
});