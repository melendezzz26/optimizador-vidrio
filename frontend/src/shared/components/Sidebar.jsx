import { House, PackagePlus, Layers3, ChartColumn, ShieldCheck, Settings } from 'lucide-react';
import {
  canConfigureOptimizer,
  canManageOrders,
  canManageUsers,
  canViewInventory,
  canViewResults,
} from '../../features/authentication/permissions';
import './ui.css';

const sections = [
  { id: 'home', label: 'Inicio', icon: House, canView: () => true },
  { id: 'orders', label: 'Registro de pedidos', icon: PackagePlus, canView: canManageOrders },
  { id: 'inventory', label: 'Gestión de inventario', icon: Layers3, canView: canViewInventory },
  { id: 'results', label: 'Consulta de resultados', icon: ChartColumn, canView: canViewResults },
  { id: 'roles', label: 'Panel de roles', icon: ShieldCheck, canView: canManageUsers },
  { id: 'configuration', label: 'Configuración', icon: Settings, canView: canConfigureOptimizer },
];

// Presentación de los módulos: no expone enlaces ni controles sin un flujo real.
export function Sidebar({ activeItem, user }) {
  const visibleSections = sections.filter(({ canView }) => canView(user));

  return (
    <aside className="ng-ui ng-sidebar" aria-label="Módulos de NewGlass">
      <div className="ng-sidebar__brand">
        <Layers3 size={32} aria-hidden="true" />
        <span>NewGlass<small>Especialistas en vidrio</small></span>
      </div>
      <ul className="ng-sidebar__list">
        {visibleSections.map(({ id, label, icon: Icon }) => (
          <li key={id} className={`ng-sidebar__item${id === activeItem ? ' ng-sidebar__item--active' : ''}`}
            aria-current={id === activeItem ? 'page' : undefined}>
            <Icon size={20} aria-hidden="true" />
            <span>{label}</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
