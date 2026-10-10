import { CircleAlert } from 'lucide-react';
import './feedback.css';

// El control inválido lo enlaza con aria-describedby={id} y marca aria-invalid="true".
export function FieldError({ id, children }) {
  if (!children) return null;

  return (
    <p className="ng-field-error" id={id}>
      <CircleAlert className="ng-field-error__icon" size={16} aria-hidden="true" />
      <span>{children}</span>
    </p>
  );
}