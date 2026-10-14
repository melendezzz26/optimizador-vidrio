import { EmptyState, FeedbackMessage, LoadingState } from '../../shared/components/feedback';

// Shared presentation of the source states already resolved by useDashboard.
export function DashboardSource({ block, label, emptyTitle, children }) {
  if (block.status === 'loading') return <LoadingState>Cargando {label.toLowerCase()}...</LoadingState>;
  if (block.status === 'error') return <FeedbackMessage variant="error" title={`No se pudo cargar ${label.toLowerCase()}`}>
    {block.error}
  </FeedbackMessage>;
  if (block.status === 'empty') return <EmptyState title={emptyTitle} />;
  return children;
}
