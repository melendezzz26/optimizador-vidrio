import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { AppShell } from '../../shared/components/AppShell';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import RegistrarPlanchaForm from './RegistrarPlanchaForm';
import { createPlancha, getPlanchas, getRetazos, getTiposVidrio } from './inventoryApi';
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

function InventoryTable({ kind, rows, typesById }) {
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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [operationError, setOperationError] = useState('');
  const [operationSuccess, setOperationSuccess] = useState('');
  const titleId = useId();
  const tabPanelId = useId();
  const tabRefs = useRef({});

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
    setOperationError('');
    setOperationSuccess('');
    setShowPlanchaForm(true);
  }

  function handleCancelPlancha() {
    setShowPlanchaForm(false);
    setOperationError('');
    setOperationSuccess('');
  }

  async function handleCreatePlancha(payload) {
    setOperationError('');
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
        setOperationError('La plancha fue registrada, pero no se pudo actualizar el listado.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  const typesById = new Map(catalogo.map((tipo) => [tipo.id_tipo_vidrio, tipo.nombre]));
  const rows = activeTab === 'planchas' ? planchas : retazos;
  const emptyMessage = activeTab === 'planchas'
    ? 'No hay planchas registradas.'
    : 'No hay retazos registrados.';

  function handleTabKeyDown(event, tabId) {
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
    setActiveTab(nextTab);
    setShowPlanchaForm(false);
    setOperationError('');
    setOperationSuccess('');
  }

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
              aria-controls={`${tabPanelId}-${tab.id}`}
              id={`${tabPanelId}-tab-${tab.id}`}
              tabIndex={activeTab === tab.id ? 0 : -1}
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

      {operationSuccess && !showPlanchaForm && activeTab === 'planchas' && (
        <p className="inventory-status" role="status">{operationSuccess}</p>
      )}

      {operationError && activeTab === 'planchas' && (
        <p className="inventory-error" role="alert">{operationError}</p>
      )}

      {showPlanchaForm && activeTab === 'planchas' && (
        <RegistrarPlanchaForm
          catalogo={catalogo}
          onSubmit={handleCreatePlancha}
          isSubmitting={isSubmitting}
          onCancel={handleCancelPlancha}
        />
      )}

      {!isLoading && !loadError && !showPlanchaForm && (
        <PageCard
          as="section"
          className="inventory-list"
          id={`${tabPanelId}-${activeTab}`}
          role="tabpanel"
          aria-labelledby={`${tabPanelId}-tab-${activeTab}`}
        >
          <h2>{activeTab === 'planchas' ? 'Planchas registradas' : 'Retazos registrados'}</h2>
          {activeTab === 'planchas' && (
            <ActionBar>
              <button className="ng-button ng-button--primary" type="button" onClick={openPlanchaForm}>
                Registrar plancha
              </button>
            </ActionBar>
          )}
          {rows.length === 0 ? (
            <p className="inventory-status">{emptyMessage}</p>
          ) : (
            <InventoryTable kind={activeTab} rows={rows} typesById={typesById} />
          )}
        </PageCard>
      )}
    </AppShell>
  );
}
