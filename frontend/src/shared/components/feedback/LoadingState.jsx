import { LoaderCircle } from 'lucide-react';
import '../ui.css';
import './feedback.css';

export function LoadingState({ children = 'Cargando…' }) {
  return (
    <div className="ng-loading-state" role="status">
      <LoaderCircle className="ng-loading-icon" size={20} aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}