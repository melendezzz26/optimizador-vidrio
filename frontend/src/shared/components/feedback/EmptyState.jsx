import { Inbox, SearchX } from 'lucide-react';
import './feedback.css';

// "sin-datos": todavía no existe ningún registro. "sin-resultados": hay registros, pero los filtros no coinciden.
const ICONS = { 'sin-datos': Inbox, 'sin-resultados': SearchX };

export function EmptyState({ kind = 'sin-datos', title, description, action }) {
  const Icon = ICONS[kind] ?? Inbox;

  return (
    <div className="ng-empty-state" role="status">
      <Icon className="ng-empty-state__icon" size={32} aria-hidden="true" />
      <p className="ng-empty-state__title">{title}</p>
      {description && <p className="ng-empty-state__description">{description}</p>}
      {action && <div className="ng-empty-state__action">{action}</div>}
    </div>
  );
}