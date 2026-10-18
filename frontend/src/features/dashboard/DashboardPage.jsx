import { canViewDashboard } from '../authentication';
import { RefreshCw } from 'lucide-react';
import { AppShell } from '../../shared/components/AppShell';
import { PageCard, PageHeader } from '../../shared/components/PageLayout';
import { FeedbackMessage } from '../../shared/components/feedback';
import { useDashboard } from './useDashboard';
import { DashboardSummary } from './DashboardSummary';
import { DashboardOrders } from './DashboardOrders';
import { DashboardQuickActions } from './DashboardQuickActions';
import './DashboardPage.css';

function DashboardWorkspace(props) {
  const { blocks, status, refresh, actions } = useDashboard(props);
  const loading = Object.values(blocks).some(block => block.status === 'loading');
  const failed = status === 'error' || status === 'partial-error';
  return <PageCard className="dashboard-page">
    <div className="dashboard-heading">
      <PageHeader title="Inicio" context="NewGlass" description="Resumen operativo de la información disponible para tu rol." />
      <button type="button" className="ng-button" onClick={refresh} disabled={loading} aria-busy={loading}>
        <RefreshCw size={18} aria-hidden="true" />{failed ? 'Reintentar carga' : 'Actualizar datos'}
      </button>
    </div>
    {status === 'partial-error' && <FeedbackMessage variant="warning" title="Información parcial">
      Algunas consultas no pudieron completarse. Cada bloque identifica su resultado; los datos válidos siguen disponibles.
    </FeedbackMessage>}
    {status === 'error' ? <FeedbackMessage variant="error" title="Información no disponible">
      No se pudo cargar el resumen. Reintenta la carga; también puedes acceder a tus funciones habilitadas.
    </FeedbackMessage> : <>
      <DashboardSummary blocks={blocks} />
      <DashboardOrders block={blocks.recentOrders} />
    </>}
    <DashboardQuickActions actions={actions} />
  </PageCard>;
}

export function DashboardPage({ user, toolbar, ...props }) {
  return <AppShell activeItem="dashboard" user={user}>
    {toolbar}
    {canViewDashboard(user) ? <DashboardWorkspace {...props} user={user} />
      : <FeedbackMessage variant="error">No tienes acceso a Inicio.</FeedbackMessage>}
  </AppShell>;
}
