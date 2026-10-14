import { useId } from 'react';
import { DashboardSource } from './DashboardSource';

const stateLabels = { PENDIENTE: 'Pendiente', EN_OPTIMIZACION: 'En optimización', OPTIMIZADO: 'Optimizado', CONFIRMADO: 'Confirmado', CANCELADO: 'Cancelado' };
const dates = new Intl.DateTimeFormat('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' });
const number = new Intl.NumberFormat('es-PE');

export function DashboardOrders({ block }) {
  const id = useId();
  if (!block) return null;
  const data = block.data;
  return <section className="dashboard-orders-section" aria-labelledby={id}>
    <h2 id={id} className="dashboard-section-title">Pedidos en orden de gestión</h2>
    <DashboardSource block={block} label="Pedidos en orden de gestión" emptyTitle="Esta página no contiene pedidos.">
      {data && <>
        <p className="dashboard-section-description">{data.orderDescription} Mostrando {number.format(data.items.length)} de {number.format(data.total)} pedidos.</p>
        <ul className="dashboard-orders" aria-label="Pedidos en orden de gestión">
          {data.items.map(item => <li key={item.id}>
            <div className="dashboard-order-identity"><h3>Pedido #{item.id}</h3><p>{item.client}</p></div>
            <div className="dashboard-order-context">
              <span className="dashboard-order-state">{stateLabels[item.state]}</span>
              <time dateTime={item.registeredAt}>{dates.format(new Date(item.registeredAt))}</time>
            </div>
          </li>)}
        </ul>
      </>}
    </DashboardSource>
  </section>;
}
