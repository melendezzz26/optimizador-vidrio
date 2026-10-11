import { useEffect, useId, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Eye, FileEdit, Plus, Search, Trash2, X } from 'lucide-react';
import { AppShell } from '../../shared/components/AppShell';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import { ConfirmDialog, EmptyState, FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import FormularioPedido from './FormularioPedido';
import { cancelOrder, listOrders } from './ordersApi';
import './GestionPedidos.css';

const PAGE_SIZE = 10;
const EMPTY_FILTERS = { estado: '', cliente: '', fecha: '' };
const NOOP = () => {};

const STATUS_LABELS = {
  PENDIENTE: 'Pendiente',
  EN_OPTIMIZACION: 'En optimización',
  OPTIMIZADO: 'Optimizado',
  CONFIRMADO: 'Confirmado',
  CANCELADO: 'Cancelado',
};

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Fecha no disponible'
    : date.toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

export default function GestionPedidos({ token, user, toolbar, onSessionExpired = NOOP }) {
  const [pedidos, setPedidos] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [feedback, setFeedback] = useState(null);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroCliente, setFiltroCliente] = useState('');
  const [filtroFecha, setFiltroFecha] = useState('');
  const [filtrosActivos, setFiltrosActivos] = useState(EMPTY_FILTERS);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [orderModal, setOrderModal] = useState(null);
  const [orderToCancel, setOrderToCancel] = useState(null);
  const [pendingCancelId, setPendingCancelId] = useState(null);
  const [isFormSubmitting, setIsFormSubmitting] = useState(false);
  const requestIdRef = useRef(0);
  const cancelInProgressRef = useRef(false);
  const modalTriggerRef = useRef(null);
  const modalRef = useRef(null);
  const modalCloseRef = useRef(null);
  const titleId = useId();

  useEffect(() => {
    const controller = new AbortController();
    const requestId = ++requestIdRef.current;
    let active = true;

    listOrders({ page, limit: PAGE_SIZE, ...filtrosActivos }, { signal: controller.signal, token })
      .then((data) => {
        if (!active || requestId !== requestIdRef.current) return;
        const pageCount = data.total_pages ?? 0;
        setTotalItems(data.total ?? 0);
        setTotalPages(pageCount);
        if (pageCount > 0 && page > pageCount) {
          setIsLoading(true);
          setPage(pageCount);
          return;
        }
        setPedidos(data.items ?? []);
      })
      .catch((error) => {
        if (!active || requestId !== requestIdRef.current || error.name === 'AbortError') return;
        if (error.status === 401) onSessionExpired();
        setLoadError(error.message || 'No se pudieron cargar los pedidos.');
      })
      .finally(() => {
        if (active && requestId === requestIdRef.current) setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [page, filtrosActivos, refreshVersion, token, onSessionExpired]);

  useEffect(() => {
    if (!orderModal) return undefined;
    modalCloseRef.current?.focus();
    return () => modalTriggerRef.current?.focus?.();
  }, [orderModal]);

  const applyFilters = (event) => {
    event.preventDefault();
    setFeedback(null);
    setLoadError('');
    setIsLoading(true);
    setPage(1);
    setFiltrosActivos({ estado: filtroEstado, cliente: filtroCliente.trim(), fecha: filtroFecha });
    setRefreshVersion((version) => version + 1);
  };

  const goToPage = (nextPage) => {
    setLoadError('');
    setIsLoading(true);
    setPage(nextPage);
  };

  const openOrderModal = (mode, orderId = null, trigger = document.activeElement) => {
    modalTriggerRef.current = trigger;
    setIsFormSubmitting(false);
    setOrderModal({ mode, orderId });
  };

  const closeOrderModal = () => {
    if (isFormSubmitting) return;
    setOrderModal(null);
  };

  const handleOrderSaved = (mode) => {
    setFeedback({
      variant: 'success',
      message: mode === 'create' ? 'Pedido creado correctamente.' : 'Pedido actualizado correctamente.',
    });
    setLoadError('');
    setIsLoading(true);
    if (mode === 'create') setPage(1);
    setRefreshVersion((version) => version + 1);
  };

  const handleCancelOrder = async () => {
    if (!orderToCancel || cancelInProgressRef.current) return;
    const orderId = orderToCancel.id_pedido;
    cancelInProgressRef.current = true;
    setPendingCancelId(orderId);
    setFeedback(null);
    try {
      await cancelOrder(orderId, { token });
      setOrderToCancel(null);
      setFeedback({ variant: 'success', message: `Pedido #${orderId} cancelado correctamente.` });
      setLoadError('');
      setIsLoading(true);
      setRefreshVersion((version) => version + 1);
    } catch (error) {
      if (error.status === 401) onSessionExpired();
      setOrderToCancel(null);
      setFeedback({ variant: 'error', message: error.message || 'No se pudo cancelar el pedido.' });
    } finally {
      cancelInProgressRef.current = false;
      setPendingCancelId(null);
    }
  };

  const handleModalKeyDown = (event) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      if (!isFormSubmitting) closeOrderModal();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = [...modalRef.current.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    )].filter((element) => !element.hasAttribute('hidden'));
    if (!focusable.length) {
      event.preventDefault();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement === modalRef.current)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const hasActiveFilters = Object.values(filtrosActivos).some(Boolean);
  const pageLabel = totalPages === 0
    ? `${totalItems} pedidos para mostrar`
    : `Página ${page} de ${totalPages} (${totalItems} pedidos)`;

  return (
    <AppShell activeItem="orders" user={user}>
      {toolbar}
      <PageHeader
        context="Pedidos"
        title="Gestión de pedidos"
        description="Busca, filtra y administra los pedidos de tus clientes."
      >
        <ActionBar>
          <button className="ng-button ng-button--primary" type="button"
            onClick={(event) => openOrderModal('create', null, event.currentTarget)}>
            <Plus size={18} aria-hidden="true" /> Nuevo pedido
          </button>
        </ActionBar>
      </PageHeader>

      {feedback && <FeedbackMessage variant={feedback.variant}>{feedback.message}</FeedbackMessage>}
      {loadError && <FeedbackMessage variant="error" title="No se pudieron cargar los pedidos">{loadError}</FeedbackMessage>}

      <PageCard as="section" className="orders-management-list" aria-labelledby={`${titleId}-list`}>
        <div className="orders-management-list__header">
          <h2 id={`${titleId}-list`}>Pedidos registrados</h2>
          <p className="orders-management-list__count" role="status" aria-live="polite">{totalItems} pedidos</p>
        </div>

        <form className="orders-management-filters" onSubmit={applyFilters}>
          <div className="ng-field">
            <label htmlFor={`${titleId}-cliente`}>Buscar por cliente</label>
            <input className="ng-control" id={`${titleId}-cliente`} type="search"
              placeholder="Ej.: Constructora XYZ" value={filtroCliente}
              onChange={(event) => setFiltroCliente(event.target.value)} />
          </div>
          <div className="ng-field">
            <label htmlFor={`${titleId}-estado`}>Estado</label>
            <select className="ng-control" id={`${titleId}-estado`} value={filtroEstado}
              onChange={(event) => setFiltroEstado(event.target.value)}>
              <option value="">Todos los estados</option>
              <option value="PENDIENTE">Pendiente</option>
              <option value="EN_OPTIMIZACION">En optimización</option>
              <option value="OPTIMIZADO">Optimizado</option>
              <option value="CONFIRMADO">Confirmado</option>
              <option value="CANCELADO">Cancelado</option>
            </select>
          </div>
          <div className="ng-field">
            <label htmlFor={`${titleId}-fecha`}>Fecha de registro</label>
            <input className="ng-control" id={`${titleId}-fecha`} type="date" value={filtroFecha}
              onChange={(event) => setFiltroFecha(event.target.value)} />
          </div>
          <div className="orders-management-filters__actions">
            <button className="ng-button ng-button--primary" type="submit">
              <Search size={18} aria-hidden="true" /> Aplicar filtros
            </button>
          </div>
        </form>

        {isLoading ? (
          <div className="orders-management-state" aria-busy="true"><LoadingState>Cargando pedidos...</LoadingState></div>
        ) : loadError ? null : pedidos.length === 0 ? (
          <EmptyState
            kind={hasActiveFilters ? 'sin-resultados' : 'sin-datos'}
            title={hasActiveFilters ? 'No hay pedidos para estos filtros.' : 'Todavía no hay pedidos registrados.'}
            description={hasActiveFilters ? 'Ajusta los filtros y vuelve a buscar.' : undefined}
          />
        ) : (
          <div className="orders-management-table-wrap">
            <table className="orders-management-table">
              <thead>
                <tr>
                  <th scope="col">Pedido</th>
                  <th scope="col">Fecha de registro</th>
                  <th scope="col">Cliente</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {pedidos.map((pedido) => (
                  <tr key={pedido.id_pedido}>
                    <th scope="row">#{pedido.id_pedido}</th>
                    <td>{formatDate(pedido.fecha_registro)}</td>
                    <td>{pedido.cliente || 'Consumidor final'}</td>
                    <td><span className={`orders-status orders-status--${pedido.estado.toLowerCase()}`}>
                      {STATUS_LABELS[pedido.estado] ?? pedido.estado}
                    </span></td>
                    <td>
                      <div className="orders-management-row-actions">
                        <button type="button" className="ng-button" aria-label={pedido.estado === 'PENDIENTE' ? `Editar pedido ${pedido.id_pedido}` : `Ver pedido ${pedido.id_pedido}`}
                          onClick={(event) => openOrderModal(pedido.estado === 'PENDIENTE' ? 'edit' : 'view', pedido.id_pedido, event.currentTarget)}>
                          {pedido.estado === 'PENDIENTE'
                            ? <><FileEdit size={16} aria-hidden="true" /> Editar</>
                            : <><Eye size={16} aria-hidden="true" /> Ver detalle</>}
                        </button>
                        {pedido.estado === 'PENDIENTE' && (
                          <button type="button" className="ng-button ng-button--danger"
                            aria-label={`Cancelar pedido ${pedido.id_pedido}`}
                            disabled={pendingCancelId === pedido.id_pedido}
                            onClick={(event) => {
                              modalTriggerRef.current = event.currentTarget;
                              setOrderToCancel(pedido);
                            }}>
                            <Trash2 size={16} aria-hidden="true" /> Cancelar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <nav className="orders-management-pagination" aria-label="Paginación de pedidos">
          <span>{pageLabel}</span>
          <div>
            <button type="button" className="ng-button" aria-label="Página anterior"
              disabled={totalPages === 0 || page <= 1} onClick={() => goToPage(Math.max(1, page - 1))}>
              <ChevronLeft size={18} aria-hidden="true" /> Anterior
            </button>
            <button type="button" className="ng-button" aria-label="Página siguiente"
              disabled={totalPages === 0 || page >= totalPages} onClick={() => goToPage(page + 1)}>
              Siguiente <ChevronRight size={18} aria-hidden="true" />
            </button>
          </div>
        </nav>
      </PageCard>

      {orderModal && (
        <div className="orders-modal-backdrop">
          <section ref={modalRef} className="orders-modal" role="dialog" aria-modal="true"
            aria-labelledby={`${titleId}-modal`} onKeyDown={handleModalKeyDown}>
            <header className="orders-modal__header">
              <h2 id={`${titleId}-modal`}>
                {orderModal.mode === 'create'
                  ? 'Crear pedido'
                  : `Pedido #${orderModal.orderId}${orderModal.mode === 'view' ? ' · Detalle' : ' · Editar'}`}
              </h2>
              <button ref={modalCloseRef} type="button" className="ng-button"
                aria-label="Cerrar formulario de pedido" disabled={isFormSubmitting} onClick={closeOrderModal}>
                <X size={18} aria-hidden="true" />
              </button>
            </header>
            <div className="orders-modal__content">
              <FormularioPedido
                token={token}
                idPedido={orderModal.orderId}
                mode={orderModal.mode}
                onCerrar={closeOrderModal}
                onSuccess={() => handleOrderSaved(orderModal.mode)}
                onSubmittingChange={setIsFormSubmitting}
              />
            </div>
          </section>
        </div>
      )}

      <ConfirmDialog
        open={orderToCancel !== null}
        title={orderToCancel ? `¿Cancelar el pedido #${orderToCancel.id_pedido}?` : ''}
        confirmLabel="Sí, cancelar pedido"
        onConfirm={handleCancelOrder}
        onCancel={() => { if (!cancelInProgressRef.current) setOrderToCancel(null); }}
        isConfirming={pendingCancelId !== null}
      >
        <p>El pedido se marcará como cancelado. Sus datos y piezas se conservarán.</p>
      </ConfirmDialog>
    </AppShell>
  );
}
