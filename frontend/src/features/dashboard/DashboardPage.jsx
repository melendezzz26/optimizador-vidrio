import { canViewDashboard } from '../authentication';
import { AppShell } from '../../shared/components/AppShell';
import { PageCard, PageHeader } from '../../shared/components/PageLayout';
import { EmptyState, FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import { DASHBOARD_SOURCES } from './dashboardModel';
import { useDashboard } from './useDashboard';

function SourceSummary({ source, data }) {
  if (source === 'planchas') return <p>Registros activos con unidades: {data.activeRecords}. Unidades registradas activas: {data.activeUnits}.</p>;
  if (source === 'retazos' || source === 'clients') return <p>Registros activos: {data.activeRecords}. Registros totales: {data.totalRecords}.</p>;
  if (source === 'recentOrders') return <p>Registros en esta página: {data.items.length}. {data.orderDescription}</p>;
  return <p>Total: {data.total}.</p>;
}

function DashboardWorkspace(props) {
  const { blocks, status, refresh } = useDashboard(props);
  return <PageCard>
    <PageHeader title="Inicio" context="NewGlass" description="Consulta la información operativa disponible para tu rol." />
    <button type="button" className="ng-button" onClick={refresh} disabled={Object.values(blocks).some(block => block.status === 'loading')}>Actualizar datos</button>
    {status === 'partial-error' && <FeedbackMessage variant="warning">Parte de la información no pudo cargarse. Los demás datos siguen disponibles.</FeedbackMessage>}
    <div aria-label="Fuentes del dashboard">
      {Object.entries(blocks).map(([source, block]) => <section key={source} aria-label={DASHBOARD_SOURCES[source]}>
        <h2>{DASHBOARD_SOURCES[source]}</h2>
        {block.status === 'loading' ? <LoadingState>Cargando {DASHBOARD_SOURCES[source].toLowerCase()}...</LoadingState>
          : block.status === 'error' ? <FeedbackMessage variant="error">{block.error}</FeedbackMessage>
            : block.status === 'empty' ? <EmptyState title="No hay registros para este resumen." />
              : <SourceSummary source={source} data={block.data} />}
      </section>)}
    </div>
  </PageCard>;
}

// T1 intentionally supplies only the functional shell and textual data states.
export function DashboardPage({ user, toolbar, ...props }) {
  return <AppShell activeItem="dashboard" user={user}>
    {toolbar}
    {canViewDashboard(user) ? <DashboardWorkspace {...props} user={user} />
      : <FeedbackMessage variant="error">No tienes acceso a Inicio.</FeedbackMessage>}
  </AppShell>;
}
