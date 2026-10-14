import { useContext, useEffect, useMemo, useState } from 'react';
import { ArrowRight, ArrowUpRight, Boxes, ClipboardList, FilePlus2, Layers3, Recycle, Scissors, Users } from 'lucide-react';
import { AppShell } from '../../shared/components/AppShell';
import { NavigationContext } from '../../shared/components/NavigationContext';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import { EmptyState, FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import { OrderStatusBadge } from '../orders';
import { loadDashboardData } from './dashboardData';
import './dashboard.css';

const NOOP = () => {};

function formatCount(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—';
  return new Intl.NumberFormat('es-CO', { maximumFractionDigits: 0 }).format(Number(value));
}

function formatDate(value) {
  const date = new Date(value);
  if (!value || Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium' }).format(date);
}

function inventoryCount(items, field) {
  if (!Array.isArray(items)) return null;
  return items.reduce((total, item) => {
    if (!item.estado) return total;
    return total + (field ? Number(item[field]) || 0 : 1);
  }, 0);
}

function StatCard({ icon: Icon, title, value, detail, index = 0 }) {
  return (
    <article className="dashboard-stat" style={{ '--dash-index': index }}>
      <span className="dashboard-stat__icon"><Icon size={19} strokeWidth={1.9} aria-hidden="true" /></span>
      <h3 className="dashboard-stat__label">{title}</h3>
      <p className="dashboard-stat__value" aria-label={`${title}: ${value}`}>{value}</p>
      <p className="dashboard-stat__detail">{detail}</p>
    </article>
  );
}

function QuickAction({ icon: Icon, label, description, onClick, tone = 'blue' }) {
  return (
    <button className={`dashboard-quick-action dashboard-quick-action--${tone}`} type="button" onClick={onClick}>
      <span className="dashboard-quick-action__icon"><Icon size={19} aria-hidden="true" /></span>
      <span className="dashboard-quick-action__copy">
        <strong>{label}</strong>
        <small>{description}</small>
      </span>
      <ArrowUpRight className="dashboard-quick-action__arrow" size={16} aria-hidden="true" />
    </button>
  );
}

function InventorySummary({ inventory, loading, onNavigate }) {
  const rows = useMemo(() => {
    if (!inventory) return [];
    const materialNames = new Map((inventory.materials ?? []).map((item) => (
      [Number(item.id_tipo_vidrio), item.nombre]
    )));
    const typeIds = new Set([
      ...(inventory.materials ?? []).map((item) => Number(item.id_tipo_vidrio)),
      ...(inventory.sheets ?? []).map((item) => Number(item.id_tipo_vidrio)),
      ...(inventory.offcuts ?? []).map((item) => Number(item.id_tipo_vidrio)),
    ]);

    return [...typeIds].sort((first, second) => first - second).map((typeId) => ({
      id: typeId,
      name: materialNames.get(typeId) ?? `Material #${typeId}`,
      sheets: Array.isArray(inventory.sheets)
        ? inventory.sheets.filter((item) => item.estado && Number(item.id_tipo_vidrio) === typeId)
          .reduce((total, item) => total + (Number(item.cantidad) || 0), 0)
        : null,
      offcuts: Array.isArray(inventory.offcuts)
        ? inventory.offcuts.filter((item) => item.estado && Number(item.id_tipo_vidrio) === typeId).length
        : null,
    }));
  }, [inventory]);

  const errors = [
    inventory?.sheetError && `Planchas: ${inventory.sheetError.message}`,
    inventory?.offcutError && `Retazos: ${inventory.offcutError.message}`,
    inventory?.materialsError && `Tipos de vidrio: ${inventory.materialsError.message}`,
  ].filter(Boolean);

  return (
    <PageCard as="section" className="dashboard-panel dashboard-inventory" aria-labelledby="dashboard-inventory-title">
      <div className="dashboard-panel__header">
        <div>
          <span className="dashboard-panel__eyebrow">Existencias actuales</span>
          <h2 id="dashboard-inventory-title">Resumen de inventario</h2>
        </div>
        <button type="button" className="dashboard-text-button" onClick={() => onNavigate('inventory')}>
          Inventario <ArrowRight size={16} aria-hidden="true" />
        </button>
      </div>
      {loading ? (
        <LoadingState>Cargando inventario…</LoadingState>
      ) : errors.length > 0 && rows.length === 0 ? (
        <FeedbackMessage variant="error" title="No se pudo cargar el inventario">{errors.join(' ')}</FeedbackMessage>
      ) : rows.length === 0 ? (
        <EmptyState title="No hay materiales registrados todavía." description="Cuando se registren tipos de vidrio, las existencias aparecerán aquí." />
      ) : (
        <>
          <ul className="dashboard-inventory-list">
            {rows.map((row) => (
              <li key={row.id}>
                <strong>{row.name}</strong>
                <span><b>{formatCount(row.sheets)}</b> planchas <i aria-hidden="true">·</i> <b>{formatCount(row.offcuts)}</b> retazos</span>
              </li>
            ))}
          </ul>
          {errors.map((message) => <FeedbackMessage key={message} variant="warning">{message}</FeedbackMessage>)}
        </>
      )}
    </PageCard>
  );
}

function RecentOrders({ orders, total, loading, error, detailsPartial, onNavigate }) {
  return (
    <PageCard as="section" className="dashboard-panel dashboard-recent" aria-labelledby="dashboard-recent-title">
      <div className="dashboard-panel__header">
        <div>
          <span className="dashboard-panel__eyebrow">Actividad reciente</span>
          <h2 id="dashboard-recent-title">Pedidos recientes</h2>
        </div>
        <div className="dashboard-panel__header-actions">
          {total !== null && <span className="dashboard-total-count">{formatCount(total)} registrados</span>}
          <button type="button" className="dashboard-text-button" onClick={() => onNavigate('orders')}>
            Ver pedidos <ArrowRight size={16} aria-hidden="true" />
          </button>
        </div>
      </div>
      {loading ? (
        <LoadingState>Cargando pedidos recientes…</LoadingState>
      ) : error ? (
        <FeedbackMessage variant="error" title="No se pudieron cargar los pedidos">{error.message}</FeedbackMessage>
      ) : orders.length === 0 ? (
        <EmptyState title="No hay pedidos registrados todavía." description="Al crear un pedido aparecerá aquí con su estado y detalle." />
      ) : (
        <>
          {detailsPartial && <FeedbackMessage variant="warning">Algunos detalles de piezas no están disponibles en este momento.</FeedbackMessage>}
          <div className="dashboard-table-scroll" role="region" aria-label="Tabla de pedidos recientes" tabIndex={0}>
            <table className="dashboard-orders-table">
              <thead>
                <tr>
                  <th scope="col">ID</th>
                  <th scope="col">Cliente</th>
                  <th scope="col">Vidrio / resumen</th>
                  <th scope="col" className="dashboard-table-number">Piezas</th>
                  <th scope="col">Fecha</th>
                  <th scope="col">Estado</th>
                  <th scope="col" className="dashboard-table-actions-heading">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <th scope="row">#{order.id}</th>
                    <td className="dashboard-order-client">{order.client}</td>
                    <td className="dashboard-order-glass">{order.glassSummary ?? '—'}</td>
                    <td className="dashboard-table-number">{formatCount(order.pieceCount)}</td>
                    <td>{formatDate(order.date)}</td>
                    <td><OrderStatusBadge status={order.status} /></td>
                    <td>
                      <div className="dashboard-row-actions">
                        <button type="button" className="ng-button dashboard-row-action"
                          aria-label={`Ver pedido ${order.id}`}
                          onClick={() => onNavigate('orders', { order: { id: order.id, mode: 'view' } })}>Ver</button>
                        {order.status === 'PENDIENTE' && (
                          <>
                            <button type="button" className="ng-button dashboard-row-action"
                              aria-label={`Editar pedido ${order.id}`}
                              onClick={() => onNavigate('orders', { order: { id: order.id, mode: 'edit' } })}>Editar</button>
                            <button type="button" className="ng-button ng-button--danger dashboard-row-action"
                              aria-label={`Cancelar pedido ${order.id}`}
                              onClick={() => onNavigate('orders', { order: { id: order.id, mode: 'cancel' } })}>Cancelar</button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </PageCard>
  );
}

export function DashboardPage({
  token,
  user,
  canAccessOrders,
  canAccessInventory,
  canRegisterSheets,
  canRegisterOffcuts,
  onSessionExpired = NOOP,
  toolbar,
}) {
  const { onNavigate } = useContext(NavigationContext);
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    loadDashboardData({ token, canAccessOrders, canAccessInventory })
      .then((result) => {
        if (!active) return;
        setData(result);
        if (result.unauthorized) onSessionExpired();
      })
      .catch((error) => {
        if (active) setData({
          recentOrders: [], totalOrders: null, pendingOrders: [], pendingCount: null,
          inventory: canAccessInventory ? {
            sheets: null, offcuts: null, materials: null,
            sheetError: error, offcutError: error, materialsError: error,
          } : null,
          clientsCount: null,
          recentError: canAccessOrders ? error : null,
          pendingError: canAccessOrders ? error : null,
          clientsError: canAccessOrders ? error : null,
          unauthorized: false,
          recentDetailsPartial: false,
        });
      })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [token, canAccessOrders, canAccessInventory, onSessionExpired]);

  const activeSheetCount = inventoryCount(data?.inventory?.sheets, 'cantidad');
  const activeOffcutCount = inventoryCount(data?.inventory?.offcuts);
  const today = new Intl.DateTimeFormat('es-CO', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());
  const firstName = user?.nombre?.trim().split(/\s+/)[0];

  const kpis = [];
  if (canAccessInventory) {
    kpis.push(
      { title: 'Planchas disponibles', icon: Layers3, value: isLoading ? '—' : formatCount(activeSheetCount), detail: data?.inventory?.sheetError ? 'No fue posible consultar planchas' : 'Unidades activas en inventario' },
      { title: 'Retazos reutilizables', icon: Recycle, value: isLoading ? '—' : formatCount(activeOffcutCount), detail: data?.inventory?.offcutError ? 'No fue posible consultar retazos' : 'Retazos activos en inventario' },
    );
  }
  if (canAccessOrders) {
    kpis.push(
      { title: 'Pedidos pendientes', icon: ClipboardList, value: isLoading ? '—' : formatCount(data?.pendingCount), detail: data?.pendingError ? 'No fue posible consultar pedidos' : 'Estado actual: pendiente' },
      { title: 'Pedidos registrados', icon: Boxes, value: isLoading ? '—' : formatCount(data?.totalOrders), detail: 'Total informado por el listado de pedidos' },
      { title: 'Clientes registrados', icon: Users, value: isLoading ? '—' : formatCount(data?.clientsCount), detail: data?.clientsError ? 'No fue posible consultar clientes' : 'Total informado por el listado de clientes' },
    );
  }

  const actions = [
    ...(canAccessOrders ? [
      { label: 'Nuevo pedido', description: 'Crear solicitud de corte', icon: FilePlus2, view: 'new-order' },
      { label: 'Ver pedidos', description: 'Consultar y administrar pedidos', icon: ClipboardList, view: 'orders' },
    ] : []),
    ...(canAccessInventory ? [
      { label: 'Gestión de inventario', description: 'Consultar planchas y retazos', icon: Boxes, view: 'inventory' },
    ] : []),
    ...(canRegisterSheets ? [
      { label: 'Registrar plancha', description: 'Agregar planchas al inventario', icon: Layers3, view: 'register-plancha', tone: 'green' },
    ] : []),
    ...(canRegisterOffcuts ? [
      { label: 'Registrar retazo', description: 'Agregar un retazo reutilizable', icon: Scissors, view: 'register-retazo', tone: 'green' },
    ] : []),
  ];

  const indicatorErrors = [
    data?.pendingError && `Pedidos pendientes: ${data.pendingError.message}`,
    data?.clientsError && `Clientes: ${data.clientsError.message}`,
  ].filter(Boolean);

  return (
    <AppShell activeItem="dashboard" user={user}>
      {toolbar}
      <div className="dashboard-page">
        <PageHeader
          context="Centro de operaciones"
          title="Dashboard operativo"
          description="Resumen operativo de inventario, pedidos y clientes"
        >
          <div className="dashboard-header-meta">
            <span>{today}</span>
            {firstName && <span>Hola, <strong>{firstName}</strong></span>}
          </div>
          {canAccessOrders && (
            <ActionBar>
              <button className="ng-button ng-button--primary dashboard-primary-action" type="button" onClick={() => onNavigate?.('new-order')}>
                <FilePlus2 size={18} aria-hidden="true" /> Nuevo pedido
              </button>
            </ActionBar>
          )}
        </PageHeader>

        {indicatorErrors.length > 0 && (
          <FeedbackMessage variant="error" title="Algunos indicadores no están disponibles">
            <ul className="dashboard-error-list">
              {indicatorErrors.map((message) => <li key={message}>{message}</li>)}
            </ul>
          </FeedbackMessage>
        )}

        <section className="dashboard-kpis" aria-label="Indicadores operativos" aria-busy={isLoading}>
          {kpis.map((kpi, index) => <StatCard key={kpi.title} {...kpi} index={index} />)}
        </section>

        <section className="dashboard-actions" aria-labelledby="dashboard-actions-title">
          <div className="dashboard-section-heading">
            <div><span className="dashboard-panel__eyebrow">Flujo de trabajo</span><h2 id="dashboard-actions-title">Acciones rápidas</h2></div>
            <span>Accesos según los permisos de tu sesión</span>
          </div>
          <div className="dashboard-actions__grid">
            {actions.map((action) => (
              <QuickAction key={action.label} {...action} onClick={() => onNavigate?.(action.view)} />
            ))}
          </div>
        </section>

        <div className={`dashboard-content-grid${canAccessInventory ? '' : ' dashboard-content-grid--orders-only'}`}>
          {canAccessOrders && (
            <RecentOrders
              orders={data?.recentOrders ?? []}
              total={data?.totalOrders ?? null}
              loading={isLoading}
              error={data?.recentError}
              detailsPartial={data?.recentDetailsPartial}
              onNavigate={onNavigate}
            />
          )}
          {canAccessInventory && <InventorySummary inventory={data?.inventory} loading={isLoading} onNavigate={onNavigate} />}
        </div>
      </div>
    </AppShell>
  );
}
