import './OrderStatusBadge.css';

const STATUS_LABELS = {
  PENDIENTE: 'Pendiente',
  EN_OPTIMIZACION: 'En optimización',
  OPTIMIZADO: 'Optimizado',
  CONFIRMADO: 'Confirmado',
  CANCELADO: 'Cancelado',
};

export function OrderStatusBadge({ status }) {
  const normalizedStatus = String(status ?? '').toUpperCase();
  return (
    <span className={`orders-status orders-status--${normalizedStatus.toLowerCase()}`}>
      {STATUS_LABELS[normalizedStatus] ?? status ?? 'Sin estado'}
    </span>
  );
}
