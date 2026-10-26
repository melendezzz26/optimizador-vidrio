import { useId } from 'react';
import { Layers3, Package, ClipboardList, ScanLine, Users } from 'lucide-react';
import { DashboardSource } from './DashboardSource';

const number = new Intl.NumberFormat('es-PE');
const summaries = [
  { source: 'planchas', title: 'Planchas', icon: Layers3, empty: 'No hay planchas registradas.',
    description: 'Registros activos con cantidad positiva; no indica compatibilidad con un pedido.',
    metrics: [['activeUnits', 'Unidades registradas activas'], ['activeRecords', 'Registros activos con unidades'], ['totalRecords', 'Registros totales']] },
  { source: 'retazos', title: 'Retazos', icon: Package, empty: 'No hay retazos registrados.',
    description: 'Cada retazo es un registro unitario. Activo no implica compatibilidad con una pieza.',
    metrics: [['activeRecords', 'Retazos activos registrados'], ['totalRecords', 'Registros totales']] },
  { source: 'pendingOrders', title: 'Pedidos pendientes', icon: ClipboardList, empty: 'No hay pedidos pendientes.',
    description: 'Pedidos con estado PENDIENTE, considerando todos los registros de ese estado.',
    metrics: [['total', 'Total de pedidos pendientes']] },
  { source: 'inProgressOrders', title: 'Pedidos en optimización', icon: ScanLine, empty: 'No hay pedidos en optimización.',
    description: 'Pedidos con estado EN_OPTIMIZACION. Esta pantalla solo consulta su estado.',
    metrics: [['total', 'Total de pedidos en optimización']] },
  { source: 'clients', title: 'Clientes registrados', icon: Users, empty: 'No hay clientes registrados.',
    description: 'Conteo de clientes registrados y activos; sin datos personales en este resumen.',
    metrics: [['activeRecords', 'Clientes activos registrados'], ['totalRecords', 'Registros totales']] },
];

export function DashboardSummary({ blocks }) {
  const id = useId();
  const availableSummaries = summaries.filter(({ source }) => blocks[source]);
  if (!availableSummaries.length) return null;
  return <section aria-labelledby={`${id}-title`}>
    <h2 id={`${id}-title`} className="dashboard-section-title">Resumen operativo</h2>
    <p className="dashboard-section-description">Información de las consultas disponibles para tu rol.</p>
    <div className="dashboard-summary-grid">
      {availableSummaries.map(({ source, title, icon: Icon, empty, description, metrics }) => {
        const block = blocks[source];
        return <section key={source} className="dashboard-summary-card" aria-labelledby={`${id}-${source}`}>
          <div className="dashboard-card-heading"><Icon size={20} aria-hidden="true" /><h3 id={`${id}-${source}`}>{title}</h3></div>
          <DashboardSource block={block} label={title} emptyTitle={empty}>
            {block.data && <>
              <dl className="dashboard-metrics">
                {metrics.map(([field, label]) => <div key={field}><dt>{label}</dt><dd>{number.format(block.data[field])}</dd></div>)}
              </dl>
              <p className="dashboard-card-description">{description}</p>
            </>}
          </DashboardSource>
        </section>;
      })}
    </div>
  </section>;
}
