import { useContext } from 'react';
import { PackagePlus, Layers3, ShieldCheck, ScanLine } from 'lucide-react';
import { NavigationContext } from './NavigationContext';
import {
  canManageOrders,
  canExecuteOptimization,
  canManageUsers,
  canViewInventory,
} from '../../features/authentication/permissions';
import './ui.css';

const sections = [
  { id: 'orders', label: 'Registro de pedidos', icon: PackagePlus, canView: canManageOrders },
  { id: 'optimization', label: 'Optimización', icon: ScanLine, canView: canExecuteOptimization },
  { id: 'inventory', label: 'Gestión de inventario', icon: Layers3, canView: canViewInventory },
  { id: 'users', label: 'Panel de roles', icon: ShieldCheck, canView: canManageUsers },
];

export function Sidebar({ activeItem, user }) {
  const { onNavigate, availableViews } = useContext(NavigationContext);
  const current = activeItem === 'roles' ? 'users' : activeItem;
  const visibleSections = sections.filter(({ id, canView }) => availableViews ? availableViews.includes(id) : canView(user));

  return (
    <aside className="ng-ui ng-sidebar" aria-label="Módulos de NewGlass">
      <div className="ng-sidebar__brand">
        <Layers3 size={32} aria-hidden="true" />
        <span>NewGlass<small>Especialistas en vidrio</small></span>
      </div>
      <nav aria-label="Secciones"><ul className="ng-sidebar__list">
        {visibleSections.map(({ id, label, icon: Icon }) => (
          <li key={id}><button type="button" className={`ng-sidebar__item${id === current ? ' ng-sidebar__item--active' : ''}`}
            aria-current={id === current ? 'page' : undefined} disabled={!onNavigate} onClick={() => onNavigate?.(id)}>
            <Icon size={20} aria-hidden="true" />
            <span>{label}</span>
          </button></li>
        ))}
      </ul></nav>
    </aside>
  );
}
