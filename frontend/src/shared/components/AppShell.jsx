import { useId } from 'react';
import { Sidebar } from './Sidebar';
import './ui.css';

export function AppShell({ activeItem, user, children }) {
  const contentId = useId();
  return (
    <div className="ng-ui ng-app-shell">
      <a className="ng-skip-link" href={`#${contentId}`}>Saltar al contenido</a>
      <Sidebar activeItem={activeItem} user={user} />
      <main className="ng-app-shell__main" id={contentId} tabIndex={-1}>
        <div className="ng-app-shell__content">{children}</div>
      </main>
    </div>
  );
}
