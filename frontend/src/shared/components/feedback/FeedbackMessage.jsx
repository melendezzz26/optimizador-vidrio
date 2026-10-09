import { CircleAlert, CircleCheck, Info, TriangleAlert } from 'lucide-react';
import './feedback.css';

// Cada variante define su ícono, su título visible y cómo la anuncia el lector de pantalla.
const VARIANTS = {
  success: { icon: CircleCheck, label: 'Operación completada', role: 'status' },
  error: { icon: CircleAlert, label: 'Error', role: 'alert' },
  warning: { icon: TriangleAlert, label: 'Advertencia', role: 'status' },
  info: { icon: Info, label: 'Información', role: 'status' },
};

export function FeedbackMessage({ variant = 'info', title, children, className = '' }) {
  const { icon: Icon, label, role } = VARIANTS[variant] ?? VARIANTS.info;

  return (
    <div className={`ng-feedback ng-feedback--${variant} ${className}`.trim()} role={role}>
      <Icon className="ng-feedback__icon" size={20} aria-hidden="true" />
      <div className="ng-feedback__body">
        <p className="ng-feedback__title">{title ?? label}</p>
        {children && <div className="ng-feedback__text">{children}</div>}
      </div>
    </div>
  );
}