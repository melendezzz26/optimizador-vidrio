import { EmptyState, FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import { InventoryDialog } from './InventoryDialog';

const EVENT_LABELS = {
  BAJA_ROTURA: 'Baja por rotura',
  BAJA_MERMA: 'Baja por merma',
  BAJA_ERROR_REGISTRO: 'Baja por error de registro',
  BAJA_RETIRO: 'Baja por retiro',
  CONSUMO_OPTIMIZACION: 'Consumo por optimización',
};

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Fecha no disponible';
  return new Intl.DateTimeFormat('es-PE', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function MovementHistoryDialog({
  resource, kind, movements, isLoading, error, onRetry, onClose,
}) {
  const resourceId = kind === 'plancha' ? resource.id_plancha : resource.id_retazo;
  const description = kind === 'plancha'
    ? `Plancha #${resourceId}`
    : `Retazo ${resource.codigo} (#${resourceId})`;

  return (
    <InventoryDialog title={`Historial de movimientos · ${description}`} onClose={onClose}>
      <div className="inventory-dialog__body inventory-history">
        {isLoading && <LoadingState>Cargando historial de movimientos...</LoadingState>}
        {error && (
          <>
            <FeedbackMessage variant="error" title="No se pudo cargar el historial">{error}</FeedbackMessage>
            <div className="ng-action-bar">
              <button className="ng-button" type="button" onClick={onRetry}>Reintentar</button>
            </div>
          </>
        )}
        {!isLoading && !error && movements.length === 0 && (
          <EmptyState
            title="No hay movimientos registrados para este material."
            description="Las bajas y otros movimientos aparecerán aquí con su fecha y actor."
          />
        )}
        {!isLoading && !error && movements.length > 0 && (
          <ol className="inventory-history__list" aria-label="Movimientos en orden cronológico">
            {movements.map((movement) => (
              <li className="inventory-history__item" key={movement.id_movimiento}>
                <article>
                  <header className="inventory-history__header">
                    <h3>{EVENT_LABELS[movement.tipo_evento] ?? movement.tipo_evento}</h3>
                    <time dateTime={movement.fecha}>{formatDateTime(movement.fecha)}</time>
                  </header>
                  <dl className="inventory-history__details">
                    <div><dt>Cantidad afectada</dt><dd>{movement.cantidad_afectada ?? 'Desconocida (histórico)'}</dd></div>
                    <div><dt>Motivo</dt><dd>{movement.motivo}</dd></div>
                    <div><dt>Observación</dt><dd>{movement.observacion || 'Sin observación'}</dd></div>
                    <div><dt>Actor</dt><dd>Usuario #{movement.id_usuario}</dd></div>
                    {movement.id_optimizacion != null && (
                      <div><dt>Optimización</dt><dd>#{movement.id_optimizacion}</dd></div>
                    )}
                    <div><dt>Movimiento</dt><dd>#{movement.id_movimiento}</dd></div>
                  </dl>
                </article>
              </li>
            ))}
          </ol>
        )}
      </div>
    </InventoryDialog>
  );
}
