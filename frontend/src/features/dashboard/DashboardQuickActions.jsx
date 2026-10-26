import { useContext, useId } from 'react';
import { Layers3, PackagePlus, ScanLine, ShieldCheck, ArrowRight } from 'lucide-react';
import { NavigationContext } from '../../shared/components/NavigationContext';

const icons = { inventory: Layers3, orders: PackagePlus, optimization: ScanLine, users: ShieldCheck };

export function DashboardQuickActions({ actions }) {
  const { onNavigate, availableViews } = useContext(NavigationContext);
  const id = useId();
  const available = actions.filter(({ view }) => !availableViews || availableViews.includes(view));
  if (!onNavigate || !available.length) return null;
  return <section className="dashboard-quick-actions" aria-labelledby={id}>
    <h2 id={id} className="dashboard-section-title">Accesos rápidos</h2>
    <p className="dashboard-section-description">Abre una función habilitada para tu rol.</p>
    <ul>
      {available.map(action => {
        const Icon = icons[action.view];
        return <li key={action.view}><button type="button" className="ng-button dashboard-quick-action"
          aria-label={`Abrir ${action.label}`} onClick={() => onNavigate(action.view)}>
          {Icon && <Icon size={20} aria-hidden="true" />}<span>{action.label}</span><ArrowRight size={18} aria-hidden="true" />
        </button></li>;
      })}
    </ul>
  </section>;
}
