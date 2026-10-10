import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { canManagePlanchas, canManageRetazos } from '../authentication';
import { AppShell } from '../../shared/components/AppShell';
import { PageCard, PageHeader } from '../../shared/components/PageLayout';
import { ConfirmDialog, EmptyState, FeedbackMessage, LoadingState } from '../../shared/components/feedback';
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

const EMPTY_FILTERS = { tipo: '', espesor: '', estado: '' };

function filterThicknesses(catalogo, rows, typeId) {
  const values = [
    ...catalogo.filter((type) => !typeId || Number(type.id_tipo_vidrio) === Number(typeId))
      .flatMap((type) => type.espesores_mm ?? []),
    ...rows.filter((row) => !typeId || Number(row.id_tipo_vidrio) === Number(typeId))
      .map((row) => row.espesor_mm),
  ].map(Number).filter((value) => Number.isFinite(value) && value > 0);
  return [...new Set(values)].sort((a, b) => a - b);
}

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
  return typesById.get(Number(id)) || `Tipo de vidrio #${id}`;
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

function normalizedRetazoGeometry(geometria) {
  if (!geometria) return null;
  if (geometria.type === 'RECTANGULO') {
    return {
      type: 'RECTANGULO',
      width_mm: Number(geometria.width_mm),
      height_mm: Number(geometria.height_mm),
    };
  }
  if (geometria.type === 'CIRCUNFERENCIA') {
    return { type: 'CIRCUNFERENCIA', radius_mm: Number(geometria.radius_mm) };
  }
  if (geometria.type === 'POLIGONO_CONVEXO') {
    return {
      type: 'POLIGONO_CONVEXO',
      vertices_mm: geometria.vertices_mm.map(([x, y]) => [Number(x), Number(y)]),
    };
  }
  return null;
}

function retazoGeometriesEqual(left, right) {
  const first = normalizedRetazoGeometry(left);
  const second = normalizedRetazoGeometry(right);
  if (!first || !second || first.type !== second.type) return false;
  if (first.type === 'RECTANGULO') {
    return first.width_mm === second.width_mm && first.height_mm === second.height_mm;
  }
  if (first.type === 'CIRCUNFERENCIA') return first.radius_mm === second.radius_mm;
  if (first.vertices_mm.length !== second.vertices_mm.length) return false;
  return first.vertices_mm.every(([x, y], index) => (
    x === second.vertices_mm[index][0] && y === second.vertices_mm[index][1]
  ));
}

function StatusBadge({ active }) {
  return (
    <span className={`inventory-badge${active ? ' inventory-badge--active' : ''}`}>
      {active ? 'Activo' : 'Inactivo'}
    </span>
  );
}

function InventoryTable({
  kind, rows, typesById, canManage, onToggleStatus, onEditPlancha, onEditRetazo, pendingAction,
}) {
  if (kind === 'planchas') {
    return (
      <div className="inventory-table-scroll" tabIndex={0} role="region" aria-label="Tabla de planchas">
        <table className="inventory-table">
          <caption className="inventory-visually-hidden">Listado de planchas</caption>
          <thead>
            <tr>
              <th scope="col">Tipo de vidrio</th>
              <th scope="col" className="inventory-number">Espesor</th>
              <th scope="col" className="inventory-number">Ancho</th>
              <th scope="col" className="inventory-number">Alto</th>
              <th scope="col" className="inventory-number">Cantidad</th>
              <th scope="col">Estado</th>
              <th scope="col">Fecha de registro</th>
              {canManage && <th scope="col">Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((plancha) => (
              <tr key={plancha.id_plancha}>
                <th scope="row">{typeNameFor(plancha.id_tipo_vidrio, typesById)}</th>
                <td className="inventory-number">{formatNumber(plancha.espesor_mm)} mm</td>
                <td className="inventory-number">{formatNumber(plancha.ancho_mm)} mm</td>
                <td className="inventory-number">{formatNumber(plancha.alto_mm)} mm</td>
                <td className="inventory-number">{formatNumber(plancha.cantidad)}</td>
                <td><StatusBadge active={plancha.estado} /></td>
                <td>{formatDate(plancha.fecha_registro)}</td>
                {canManage && (
                  <td>
                    <div className="inventory-row-actions">
                      <button
                        className="ng-button"
                        type="button"
                        disabled={pendingAction !== null}
                        onClick={() => onEditPlancha(plancha)}
                      >
                        Editar
                      </button>
                      <button
                        className="ng-button"
                        type="button"
                        disabled={pendingAction !== null}
                        aria-busy={pendingAction?.id === plancha.id_plancha}
                        onClick={() => onToggleStatus(plancha)}
                      >
                        {plancha.estado ? 'Desactivar' : 'Activar'}
                      </button>
                    </div>
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
    <div className="inventory-table-scroll" tabIndex={0} role="region" aria-label="Tabla de retazos">
      <table className="inventory-table">
        <caption className="inventory-visually-hidden">Listado de retazos</caption>
        <thead>
          <tr>
            <th scope="col">Código</th>
            <th scope="col">Tipo de vidrio</th>
            <th scope="col" className="inventory-number">Espesor</th>
            <th scope="col">Geometría</th>
            <th scope="col" className="inventory-number">Área</th>
            <th scope="col">Estado</th>
            <th scope="col">Fecha de registro</th>
            {canManage && <th scope="col">Acciones</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((retazo) => (
            <tr key={retazo.id_retazo}>
              <th scope="row" className="inventory-code">{retazo.codigo}</th>
              <td>{typeNameFor(retazo.id_tipo_vidrio, typesById)}</td>
              <td className="inventory-number">{formatNumber(retazo.espesor_mm)} mm</td>
              <td className="inventory-geometry">{geometryDescription(retazo.geometria)}</td>
              <td className="inventory-number">{formatNumber(retazo.area_mm2)} mm²</td>
              <td><StatusBadge active={retazo.estado} /></td>
              <td>{formatDate(retazo.fecha_registro)}</td>
              {canManage && (
                <td>
                  <div className="inventory-row-actions">
                    <button
                      className="ng-button"
                      type="button"
                      disabled={pendingAction !== null}
                      onClick={() => onEditRetazo(retazo)}
                    >
                      Editar
                    </button>
                    <button
                      className="ng-button"
                      type="button"
                      disabled={pendingAction !== null}
                      aria-busy={pendingAction?.id === retazo.id_retazo}
                      onClick={() => onToggleStatus(retazo)}
                    >
                      {retazo.estado ? 'Desactivar' : 'Activar'}
                    </button>
                  </div>
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
  const [filtersByTab, setFiltersByTab] = useState({
    planchas: { ...EMPTY_FILTERS }, retazos: { ...EMPTY_FILTERS },
  });
  const [catalogo, setCatalogo] = useState([]);
  const [planchas, setPlanchas] = useState([]);
  const [retazos, setRetazos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [showPlanchaForm, setShowPlanchaForm] = useState(false);
  const [showRetazoForm, setShowRetazoForm] = useState(false);
  const [editingPlancha, setEditingPlancha] = useState(null);
  const [editingRetazo, setEditingRetazo] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [operationError, setOperationError] = useState('');
  const [operationWarning, setOperationWarning] = useState('');
  const [operationSuccess, setOperationSuccess] = useState('');
  const [pendingInventoryAction, setPendingInventoryAction] = useState(null);
  const [statusChangeToConfirm, setStatusChangeToConfirm] = useState(null);
  const titleId = useId();
  const tabPanelId = useId();
  const tabRefs = useRef({});
  const isInventoryActionPending = pendingInventoryAction !== null;

  const handleApiError = useCallback((error) => {
    if (error.status === 401) onSessionExpired('Tu sesión no es válida o ha expirado.');
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
    setEditingPlancha(null);
    setShowPlanchaForm(true);
  }

  function openRetazoForm() {
    if (isInventoryActionPending) return;
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
    setEditingRetazo(null);
    setShowRetazoForm(true);
  }

  function handleCancelPlancha() {
    setShowPlanchaForm(false);
    setEditingPlancha(null);
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
  }

  function handleCancelRetazo() {
    setShowRetazoForm(false);
    setEditingRetazo(null);
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

  function handleEditPlancha(plancha) {
    if (isInventoryActionPending) return;
    setEditingPlancha(plancha);
    setShowPlanchaForm(true);
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
  }

  async function handleUpdatePlancha(values) {
    if (!editingPlancha) return;

    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');

    const normalized = {
      ancho_mm: Number(values.ancho_mm),
      alto_mm: Number(values.alto_mm),
      espesor_mm: Number(values.espesor_mm),
      cantidad: Number(values.cantidad),
      id_tipo_vidrio: Number(values.id_tipo_vidrio),
    };
    const changes = {};
    for (const field of Object.keys(normalized)) {
      if (normalized[field] !== Number(editingPlancha[field])) changes[field] = normalized[field];
    }

    if (Object.keys(changes).length === 0) {
      setOperationWarning('No hay cambios para guardar.');
      return;
    }

    setIsSubmitting(true);
    setPendingInventoryAction({
      entity: 'plancha',
      id: editingPlancha.id_plancha,
      operation: 'edit',
    });
    try {
      try {
        await updatePlancha(editingPlancha.id_plancha, changes);
      } catch (error) {
        setOperationError(handleApiError(error).message);
        return;
      }

      try {
        const updatedPlanchas = await getPlanchas();
        setPlanchas(updatedPlanchas);
        setActiveTab('planchas');
        setShowPlanchaForm(false);
        setEditingPlancha(null);
        setOperationSuccess('Plancha actualizada correctamente.');
      } catch (error) {
        handleApiError(error);
        setActiveTab('planchas');
        setShowPlanchaForm(false);
        setEditingPlancha(null);
        setOperationWarning('La plancha fue actualizada, pero no se pudo refrescar el listado.');
      }
    } finally {
      setIsSubmitting(false);
      setPendingInventoryAction(null);
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

  function handleEditRetazo(retazo) {
    if (isInventoryActionPending) return;
    setEditingRetazo(retazo);
    setShowRetazoForm(true);
    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');
  }

  async function handleUpdateRetazo(values) {
    if (!editingRetazo) return;

    setOperationError('');
    setOperationWarning('');
    setOperationSuccess('');

    const normalized = {
      codigo: String(values.codigo).trim(),
      id_tipo_vidrio: Number(values.id_tipo_vidrio),
      espesor_mm: Number(values.espesor_mm),
    };
    const changes = {};
    if (normalized.codigo !== String(editingRetazo.codigo).trim()) {
      changes.codigo = normalized.codigo;
    }
    if (normalized.id_tipo_vidrio !== Number(editingRetazo.id_tipo_vidrio)) {
      changes.id_tipo_vidrio = normalized.id_tipo_vidrio;
    }
    if (normalized.espesor_mm !== Number(editingRetazo.espesor_mm)) {
      changes.espesor_mm = normalized.espesor_mm;
    }

    const normalizedGeometry = normalizedRetazoGeometry(values.geometria);
    if (!retazoGeometriesEqual(values.geometria, editingRetazo.geometria)) {
      changes.geometria = normalizedGeometry;
    }

    if (Object.keys(changes).length === 0) {
      setOperationWarning('No hay cambios para guardar.');
      return;
    }

    setIsSubmitting(true);
    setPendingInventoryAction({
      entity: 'retazo',
      id: editingRetazo.id_retazo,
      operation: 'edit',
    });
    try {
      try {
        await updateRetazo(editingRetazo.id_retazo, changes);
      } catch (error) {
        setOperationError(handleApiError(error).message);
        return;
      }

      try {
        const updatedRetazos = await getRetazos();
        setRetazos(updatedRetazos);
        setActiveTab('retazos');
        setShowRetazoForm(false);
        setEditingRetazo(null);
        setOperationSuccess('Retazo actualizado correctamente.');
      } catch (error) {
        handleApiError(error);
        setActiveTab('retazos');
        setShowRetazoForm(false);
        setEditingRetazo(null);
        setOperationWarning('El retazo fue actualizado, pero no se pudo refrescar el listado.');
      }
    } finally {
      setIsSubmitting(false);
      setPendingInventoryAction(null);
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

  function requestStatusChange(resource, kind) {
    if (isInventoryActionPending) return;
    if (resource.estado) {
      setStatusChangeToConfirm({ resource, kind });
      return;
    }
    if (kind === 'plancha') handleTogglePlanchaEstado(resource);
    else handleToggleRetazoEstado(resource);
  }

  async function confirmStatusChange() {
    if (!statusChangeToConfirm || isInventoryActionPending) return;
    const { resource, kind } = statusChangeToConfirm;
    if (kind === 'plancha') await handleTogglePlanchaEstado(resource);
    else await handleToggleRetazoEstado(resource);
    setStatusChangeToConfirm(null);
  }

  const typesById = new Map(catalogo.map((tipo) => [Number(tipo.id_tipo_vidrio), tipo.nombre]));
  const rows = activeTab === 'planchas' ? planchas : retazos;
  const filters = filtersByTab[activeTab];
  const hasFilters = Object.values(filters).some(Boolean);
  const filterTypes = [...new Set([
    ...catalogo.map((tipo) => Number(tipo.id_tipo_vidrio)),
    ...rows.map((row) => Number(row.id_tipo_vidrio)),
  ])].sort((a, b) => typeNameFor(a, typesById).localeCompare(typeNameFor(b, typesById), 'es'));
  const thicknesses = filterThicknesses(catalogo, rows, filters.tipo);
  const filteredRows = rows.filter((row) => (
    (!filters.tipo || Number(row.id_tipo_vidrio) === Number(filters.tipo))
    && (!filters.espesor || Number(row.espesor_mm) === Number(filters.espesor))
    && (!filters.estado || row.estado === (filters.estado === 'activo'))
  ));

  function changeFilter(field, value) {
    setFiltersByTab((previous) => {
      const next = { ...previous[activeTab], [field]: value };
      if (field === 'tipo' && next.espesor
        && !filterThicknesses(catalogo, rows, value).includes(Number(next.espesor))) {
        next.espesor = '';
      }
      return { ...previous, [activeTab]: next };
    });
  }

  function clearFilters() {
    setFiltersByTab((previous) => ({ ...previous, [activeTab]: { ...EMPTY_FILTERS } }));
  }

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
    setEditingPlancha(null);
    setEditingRetazo(null);
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

      {isLoading && (
        <PageCard className="inventory-state" aria-busy="true">
          <LoadingState>Cargando inventario...</LoadingState>
        </PageCard>
      )}
      {loadError && (
        <PageCard className="inventory-state">
          <FeedbackMessage variant="error" title="No se pudo cargar el inventario">{loadError}</FeedbackMessage>
        </PageCard>
      )}

      {operationSuccess && !showPlanchaForm && !showRetazoForm && (
        <FeedbackMessage variant="success">{operationSuccess}</FeedbackMessage>
      )}

      {operationError && (
        <FeedbackMessage variant="error" title="No se pudo completar la operación">{operationError}</FeedbackMessage>
      )}

      {operationWarning
        && (!showPlanchaForm || editingPlancha !== null)
        && (!showRetazoForm || editingRetazo !== null) && (
          <FeedbackMessage variant="warning">{operationWarning}</FeedbackMessage>
      )}

      {showPlanchaForm && activeTab === 'planchas' && (
        <RegistrarPlanchaForm
          catalogo={catalogo}
          mode={editingPlancha ? 'edit' : 'create'}
          initialValues={editingPlancha ? {
            id_tipo_vidrio: editingPlancha.id_tipo_vidrio,
            espesor_mm: editingPlancha.espesor_mm,
            ancho_mm: editingPlancha.ancho_mm,
            alto_mm: editingPlancha.alto_mm,
            cantidad: editingPlancha.cantidad,
          } : null}
          key={editingPlancha ? `edit-${editingPlancha.id_plancha}` : 'create'}
          onSubmit={editingPlancha ? handleUpdatePlancha : handleCreatePlancha}
          isSubmitting={isSubmitting}
          onCancel={handleCancelPlancha}
        />
      )}

      {showRetazoForm && activeTab === 'retazos' && (
        <RegistrarRetazoForm
          catalogo={catalogo}
          mode={editingRetazo ? 'edit' : 'create'}
          initialValues={editingRetazo ? {
            id_retazo: editingRetazo.id_retazo,
            codigo: editingRetazo.codigo,
            id_tipo_vidrio: editingRetazo.id_tipo_vidrio,
            espesor_mm: editingRetazo.espesor_mm,
            geometria: editingRetazo.geometria,
          } : null}
          key={editingRetazo ? `edit-${editingRetazo.id_retazo}` : 'create'}
          onSubmit={editingRetazo ? handleUpdateRetazo : handleCreateRetazo}
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
          <div className="inventory-list-header">
            <div>
              <h2>{activeTab === 'planchas' ? 'Planchas' : 'Retazos'}</h2>
              <p className="inventory-count" role="status" aria-live="polite" aria-atomic="true">
                Mostrando {filteredRows.length} de {rows.length} {activeTab}
              </p>
            </div>
            {canManageCurrentTab && (
              <button className="ng-button ng-button--primary" type="button"
                onClick={activeTab === 'planchas' ? openPlanchaForm : openRetazoForm}
                disabled={isInventoryActionPending}>
                {activeTab === 'planchas' ? 'Registrar plancha' : 'Registrar retazo'}
              </button>
            )}
          </div>
          <fieldset className="inventory-filters" disabled={isInventoryActionPending}>
            <legend className="inventory-visually-hidden">Filtrar {activeTab}</legend>
            <div className="ng-field">
              <label htmlFor={`${tabPanelId}-tipo`}>Tipo de vidrio</label>
              <select className="ng-control" id={`${tabPanelId}-tipo`} value={filters.tipo}
                onChange={(event) => changeFilter('tipo', event.target.value)}>
                <option value="">Todos</option>
                {filterTypes.map((id) => <option key={id} value={id}>{typeNameFor(id, typesById)}</option>)}
              </select>
            </div>
            <div className="ng-field">
              <label htmlFor={`${tabPanelId}-espesor`}>Espesor</label>
              <select className="ng-control" id={`${tabPanelId}-espesor`} value={filters.espesor}
                onChange={(event) => changeFilter('espesor', event.target.value)}>
                <option value="">Todos</option>
                {thicknesses.map((value) => <option key={value} value={value}>{formatNumber(value)} mm</option>)}
              </select>
            </div>
            <div className="ng-field">
              <label htmlFor={`${tabPanelId}-estado`}>Estado</label>
              <select className="ng-control" id={`${tabPanelId}-estado`} value={filters.estado}
                onChange={(event) => changeFilter('estado', event.target.value)}>
                <option value="">Todos</option>
                <option value="activo">Activo</option>
                <option value="inactivo">Inactivo</option>
              </select>
            </div>
          </fieldset>
          {hasFilters && (
            <div className="inventory-filter-actions">
              <button className="ng-button" type="button" onClick={clearFilters}
                disabled={isInventoryActionPending}>Limpiar filtros</button>
            </div>
          )}
          {rows.length === 0 ? (
            <EmptyState title={emptyMessage} />
          ) : filteredRows.length === 0 ? (
            <EmptyState
              kind="sin-resultados"
              title="No hay resultados para los filtros seleccionados."
              description="Ajusta los filtros o usa «Limpiar filtros» para ver todo el listado."
            />
          ) : (
            <InventoryTable
              kind={activeTab}
              rows={filteredRows}
              typesById={typesById}
              canManage={canManageCurrentTab}
              onToggleStatus={(resource) => requestStatusChange(
                resource, activeTab === 'planchas' ? 'plancha' : 'retazo',
              )}
              onEditPlancha={handleEditPlancha}
              onEditRetazo={handleEditRetazo}
              pendingAction={pendingInventoryAction}
            />
          )}
        </PageCard>
      )}
      <ConfirmDialog
        open={statusChangeToConfirm !== null}
        title="¿Desactivar material?"
        confirmLabel="Desactivar"
        onConfirm={confirmStatusChange}
        onCancel={() => setStatusChangeToConfirm(null)}
        isConfirming={isInventoryActionPending}
      >
        <p>El material dejará de aparecer como activo en el inventario.</p>
      </ConfirmDialog>
    </AppShell>
  );
}
