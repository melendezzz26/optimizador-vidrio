import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { canManagePlanchas, canManageRetazos } from '../authentication';
import { AppShell } from '../../shared/components/AppShell';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import RegistrarPlanchaForm from './RegistrarPlanchaForm';
import RegistrarRetazoForm from './RegistrarRetazoForm';
import {
  createPlancha,
  createRetazo,
  getPlanchas,
  getRetazos,
  getTiposVidrio,
  updatePlancha,
  updateRetazo,
} from './inventoryApi';
import './inventory.css';

const TABS = [
  { id: 'planchas', label: 'Planchas' },
  { id: 'retazos', label: 'Retazos' },
];

function formatNumber(value) {
  if (value === null || value === undefined || value === '') return '—';
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return '—';
  return new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 }).format(numericValue);
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium' }).format(date);
}

function typeNameFor(id, typesById) {
  return typesById.get(id) || `Tipo de vidrio #${id}`;
}

function geometryDescription(geometria) {
  if (!geometria) return 'Geometría no disponible';
  if (geometria.type === 'RECTANGULO') {
    return `Rectángulo · ${formatNumber(geometria.width_mm)} × ${formatNumber(geometria.height_mm)} mm`;
  }
  if (geometria.type === 'CIRCUNFERENCIA') {
    return `Circunferencia · radio ${formatNumber(geometria.radius_mm)} mm`;
  }
  if (geometria.type === 'POLIGONO_CONVEXO') {
    return `Polígono convexo · ${geometria.vertices_mm?.length ?? 0} vértices`;
  }
  return 'Geometría no disponible';
}

function StatusBadge({ active }) {
  return (
    <span className={`inventory-badge${active ? ' inventory-badge--active' : ''}`}>
      {active ? 'Activo' : 'Inactivo'}
    </span>
  );
}

function InventoryTable({ kind, rows, typesById, canManage, onToggleStatus, pendingAction }) {
  if (kind === 'planchas') {
    return (
      <div className="inventory-table-scroll">
        <table className="inventory-table">
          <caption className="inventory-visually-hidden">Listado de planchas</caption>
          <thead>
            <tr>
              <th scope="col">Tipo de vidrio</th>
              <th scope="col">Espesor</th>
              <th scope="col">Ancho</th>
              <th scope="col">Alto</th>
              <th scope="col">Cantidad</th>
              <th scope="col">Estado</th>
              <th scope="col">Fecha de registro</th>
              {canManage && <th scope="col">Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((plancha) => (
              <tr key={plancha.id_plancha}>
                <th scope="row">{typeNameFor(plancha.id_tipo_vidrio, typesById)}</th>
                <td>{formatNumber(plancha.espesor_mm)} mm</td>
                <td>{formatNumber(plancha.ancho_mm)} mm</td>
                <td>{formatNumber(plancha.alto_mm)} mm</td>
                <td>{formatNumber(plancha.cantidad)}</td>
                <td><StatusBadge active={plancha.estado} /></td>
                <td>{formatDate(plancha.fecha_registro)}</td>
                {canManage && (
                  <td>
                    <button
                      className="ng-button"
                      type="button"
                      disabled={pendingAction !== null}
                      aria-busy={pendingAction?.id === plancha.id_plancha}
                      onClick={() => onToggleStatus(plancha)}
                    >
                      {plancha.estado ? 'Desactivar' : 'Activar'}
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="inventory-table-scroll">
      <table className="inventory-table">
        <caption className="inventory-visually-hidden">Listado de retazos</caption>
        <thead>
          <tr>
            <th scope="col">Código</th>
            <th scope="col">Tipo de vidrio</th>
            <th scope="col">Espesor</th>
            <th scope="col">Geometría</th>
            <th scope="col">Área</th>
            <th scope="col">Estado</th>
            <th scope="col">Fecha de registro</th>
            {canManage && <th scope="col">Acciones</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((retazo) => (
            <tr key={retazo.id_retazo}>
              <th scope="row">{retazo.codigo}</th>
              <td>{typeNameFor(retazo.id_tipo_vidrio, typesById)}</td>
              <td>{formatNumber(retazo.espesor_mm)} mm</td>
              <td>{geometryDescription(retazo.geometria)}</td>
              <td>{formatNumber(retazo.area_mm2)} mm²</td>
              <td><StatusBadge active={retazo.estado} /></td>
              <td>{formatDate(retazo.fecha_registro)}</td>
              {canManage && (
                <td>
                  <button
                    className="ng-button"
                    type="button"
                    disabled={pendingAction !== null}
                    aria-busy={pendingAction?.id === retazo.id_retazo}
                    onClick={() => onToggleStatus(retazo)}
                  >
                    {retazo.estado ? 'Desactivar' : 'Activar'}
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function InventoryPage({ onSessionExpired, toolbar, user }) {
  const [activeTab, setActiveTab] = useState('planchas');
  const [catalogo, setCatalogo] = useState([]);
  const [planchas, setPlanchas] = useState([]);
  const [retazos, setRetazos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [showPlanchaForm, setShowPlanchaForm] = useState(false);
  const [showRetazoForm, setShowRetazoForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [operationError, setOperationError] = useState('');
  const [operationWarning, setOperationWarning] = useState('');
  const [operationSuccess, setOperationSuccess] = useState('');
  const [pendingInventoryAction, setPendingInventoryAction] = useState(null);
  const titleId = useId();
  const tabPanelId = useId();
  const tabRefs = useRef({});
  const isInventoryActionPending = pendingInventoryAction !== null;

  const handleApiError = useCallback((error) => {
    if (error.status === 401) onSessionExpired();
    return error;
  }, [onSessionExpired]);

  useEffect(() => {
    let active = true;
    Promise.all([getTiposVidrio(), getPlanchas(), getRetazos()])
      .then(([loadedCatalogo, loadedPlanchas, loadedRetazos]) => {
        if (!active) return;
        setCatalogo(loadedCatalogo);
        setPlanchas(loadedPlanchas);
        setRetazos(loadedRetazos);
      })
      .catch((error) => {
        if (active) setLoadError(handleApiError(error).message);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, [handleApiError]);

  function openPlanchaForm() {
    if (isInventoryActionPending) return;
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
    setShowPlanchaForm(true);
  }

  function openRetazoForm() {
    if (isInventoryActionPending) return;
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
    setShowRetazoForm(true);
  }

  function handleCancelPlancha() {
    setShowPlanchaForm(false);
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
  }

  function handleCancelRetazo() {
    setShowRetazoForm(false);
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
  }

  async function handleCreatePlancha(payload) {
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
    setIsSubmitting(true);
    try {
      try {
        await createPlancha(payload);
      } catch (error) {
        setOperationError(handleApiError(error).message);
        return;
      }

      try {
        const updatedPlanchas = await getPlanchas();
        setPlanchas(updatedPlanchas);
        setActiveTab('planchas');
        setShowPlanchaForm(false);
        setOperationSuccess('Plancha registrada correctamente.');
      } catch (error) {
        handleApiError(error);
        setActiveTab('planchas');
        setShowPlanchaForm(false);
        setOperationWarning('La plancha fue registrada, pero no se pudo actualizar el listado.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleCreateRetazo(payload) {
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
    setIsSubmitting(true);
    try {
      try {
        await createRetazo(payload);
      } catch (error) {
        setOperationError(handleApiError(error).message);
        return;
      }

      try {
        const updatedRetazos = await getRetazos();
        setRetazos(updatedRetazos);
        setActiveTab('retazos');
        setShowRetazoForm(false);
        setOperationSuccess('Retazo registrado correctamente.');
      } catch (error) {
        handleApiError(error);
        setActiveTab('retazos');
        setShowRetazoForm(false);
        setOperationWarning('El retazo fue registrado, pero no se pudo actualizar el listado.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleTogglePlanchaEstado(plancha) {
    const targetState = !plancha.estado;
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
    setPendingInventoryAction({ entity: 'plancha', id: plancha.id_plancha, targetState });
    try {
      try {
        await updatePlancha(plancha.id_plancha, { estado: targetState });
      } catch (error) {
        setOperationError(handleApiError(error).message);
        return;
      }

      try {
        const updatedPlanchas = await getPlanchas();
        setPlanchas(updatedPlanchas);
        setActiveTab('planchas');
        setOperationSuccess(`Plancha ${targetState ? 'activada' : 'desactivada'} correctamente.`);
      } catch (error) {
        handleApiError(error);
        setActiveTab('planchas');
        setOperationWarning('El estado de la plancha fue actualizado, pero no se pudo refrescar el listado.');
      }
    } finally {
      setPendingInventoryAction(null);
    }
  }

  async function handleToggleRetazoEstado(retazo) {
    const targetState = !retazo.estado;
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
    setPendingInventoryAction({ entity: 'retazo', id: retazo.id_retazo, targetState });
    try {
      try {
        await updateRetazo(retazo.id_retazo, { estado: targetState });
      } catch (error) {
        setOperationError(handleApiError(error).message);
        return;
      }

      try {
        const updatedRetazos = await getRetazos();
        setRetazos(updatedRetazos);
        setActiveTab('retazos');
        setOperationSuccess(`Retazo ${targetState ? 'activado' : 'desactivado'} correctamente.`);
      } catch (error) {
        handleApiError(error);
        setActiveTab('retazos');
        setOperationWarning('El estado del retazo fue actualizado, pero no se pudo refrescar el listado.');
      }
    } finally {
      setPendingInventoryAction(null);
    }
  }

  const typesById = new Map(catalogo.map((tipo) => [tipo.id_tipo_vidrio, tipo.nombre]));
  const rows = activeTab === 'planchas' ? planchas : retazos;
  const emptyMessage = activeTab === 'planchas'
    ? 'No hay planchas registradas.'
    : 'No hay retazos registrados.';

  function handleTabKeyDown(event, tabId) {
    if (isInventoryActionPending) return;
    const currentIndex = TABS.findIndex((tab) => tab.id === tabId);
    let nextIndex = null;

    if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % TABS.length;
    if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + TABS.length) % TABS.length;
    if (event.key === 'Home') nextIndex = 0;
    if (event.key === 'End') nextIndex = TABS.length - 1;

    if (nextIndex === null) return;
    event.preventDefault();
    const nextTab = TABS[nextIndex];
    handleTabChange(nextTab.id);
    tabRefs.current[nextTab.id]?.focus();
  }

  function handleTabChange(nextTab) {
    if (isInventoryActionPending) return;
    setActiveTab(nextTab);
    setShowPlanchaForm(false);
    setShowRetazoForm(false);
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
  }

  const canManageCurrentTab = activeTab === 'planchas'
    ? canManagePlanchas(user)
    : canManageRetazos(user);

  return (
    <AppShell activeItem="inventory" user={user}>
      {toolbar}
      <PageHeader
        context="Inventario"
        title="Gestión de Inventario"
        description="Consulta las planchas y retazos disponibles en el inventario."
        titleId={titleId}
      >
        <div className="inventory-tabs" role="tablist" aria-label="Inventario">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              className="inventory-tab"
              aria-selected={activeTab === tab.id}
              aria-disabled={isInventoryActionPending}
              aria-controls={`${tabPanelId}-${tab.id}`}
              id={`${tabPanelId}-tab-${tab.id}`}
              tabIndex={activeTab === tab.id ? 0 : -1}
              disabled={isInventoryActionPending}
              ref={(element) => { tabRefs.current[tab.id] = element; }}
              onClick={() => handleTabChange(tab.id)}
              onKeyDown={(event) => handleTabKeyDown(event, tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </PageHeader>

      {isLoading && <PageCard><p className="inventory-status" role="status">Cargando inventario...</p></PageCard>}
      {loadError && <PageCard><p className="inventory-error" role="alert">{loadError}</p></PageCard>}

      {operationSuccess && !showPlanchaForm && !showRetazoForm && (
        <p className="inventory-feedback inventory-feedback--success" role="status" aria-live="polite">
          {operationSuccess}
        </p>
      )}

      {operationError && (
        <p className="inventory-feedback inventory-feedback--error" role="alert">{operationError}</p>
      )}

      {operationWarning && !showPlanchaForm && !showRetazoForm && (
        <p className="inventory-feedback inventory-feedback--warning" role="status" aria-live="polite">
          {operationWarning}
        </p>
      )}

      {showPlanchaForm && activeTab === 'planchas' && (
        <RegistrarPlanchaForm
          catalogo={catalogo}
          onSubmit={handleCreatePlancha}
          isSubmitting={isSubmitting}
          onCancel={handleCancelPlancha}
        />
      )}

      {showRetazoForm && activeTab === 'retazos' && (
        <RegistrarRetazoForm
          catalogo={catalogo}
          onSubmit={handleCreateRetazo}
          isSubmitting={isSubmitting}
          onCancel={handleCancelRetazo}
        />
      )}

      {!isLoading && !loadError && !showPlanchaForm && !showRetazoForm && (
        <PageCard
          as="section"
          className="inventory-list"
          id={`${tabPanelId}-${activeTab}`}
          role="tabpanel"
          aria-labelledby={`${tabPanelId}-tab-${activeTab}`}
        >
          <h2>{activeTab === 'planchas' ? 'Planchas registradas' : 'Retazos registrados'}</h2>
          {activeTab === 'planchas' && canManagePlanchas(user) && (
            <ActionBar>
              <button className="ng-button ng-button--primary" type="button"
                onClick={openPlanchaForm} disabled={isInventoryActionPending}>
                Registrar plancha
              </button>
            </ActionBar>
          )}
          {activeTab === 'retazos' && canManageRetazos(user) && (
            <ActionBar>
              <button className="ng-button ng-button--primary" type="button"
                onClick={openRetazoForm} disabled={isInventoryActionPending}>
                Registrar retazo
              </button>
            </ActionBar>
          )}
          {rows.length === 0 ? (
            <p className="inventory-status">{emptyMessage}</p>
          ) : (
            <InventoryTable
              kind={activeTab}
              rows={rows}
              typesById={typesById}
              canManage={canManageCurrentTab}
              onToggleStatus={activeTab === 'planchas'
                ? handleTogglePlanchaEstado : handleToggleRetazoEstado}
              pendingAction={pendingInventoryAction}
            />
          )}
        </PageCard>
      )}
    </AppShell>
  );
}
