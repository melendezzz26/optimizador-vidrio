import { useMemo, useState } from 'react';
import { ScanLine } from 'lucide-react';
import { canExecuteOptimization, canViewResults, hasPermission } from '../authentication';
import { AppShell } from '../../shared/components/AppShell';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import { ConfirmDialog, EmptyState, FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import { createPendingOrdersSource } from './pendingOrdersSource';
import { createDemoOrdersSource, createFixtureAdapter, unavailableOptimizationAdapter } from './firstFitFixture';
import { STAGES, pieceCount } from './optimizationModel';
import { useFirstFit } from './useFirstFit';
import { PlacementCanvas } from './PlacementCanvas';
import { detectMaterialGroups } from './materialGroups';
import { MaterialGroupsPanel } from './MaterialGroupsPanel';
import { groupRasterReady } from './rasterInspectionModel';
import { parseConfirmation } from './runContract.js';
import { Hu015Rasterization } from './Hu015Rasterization';
import { createFixturePendingOrdersSource } from './pendingOrdersSource';
import './OptimizationPage.css';

function OptimizationWorkspace({ source, adapter, onSessionExpired, user, result }) {
  const flow = useFirstFit({ source, adapter, onSessionExpired, result });
  const { state } = flow;
  const [dialog, setDialog] = useState(false);
  const [confirmation, setConfirmation] = useState('');
  const canExecute = canExecuteOptimization(user);
  const canConfirm = hasPermission(user, 'optimization.confirm');
  const locked = !canExecute || ['preparing', 'running'].includes(state.status);
  const fresh = state.runId ? state.orders.filter(o => !state.availableAtStart?.includes(o.id_pedido)).length : 0;
  const stageIndex = STAGES.findIndex(([id]) => id === state.stage);
  const preview = detectMaterialGroups(state.orders.filter(o => state.selected.includes(o.id_pedido)), adapter.resolveMaterial);
  const rasterReady = state.snapshot?.groups.length > 0 && state.snapshot.groups.every(g => groupRasterReady(state.snapshot, g));
  async function confirm() {
    setDialog(false);
    try {
      if (!canConfirm || !state.confirmable || state.confirmed) return;
      parseConfirmation(await adapter.confirm(state.optimizationId), state.optimizationId);
      flow.confirmed();
      setConfirmation('Solución confirmada por el servidor.');
    } catch (error) { setConfirmation(error.status === 409 ? 'El inventario cambió (409). Recupera el resultado y solicita una nueva simulación.' : error.message); }
  }
  function reset(action) { setConfirmation(''); action(); }
  return <>
    {canExecute && <section aria-labelledby="pending-orders-title">
      <div className="first-fit-section-heading"><h2 id="pending-orders-title">Pedidos pendientes</h2>
        <span role="status">{state.connection === 'connected' ? 'Actualización automática activa' : state.connection === 'error' ? 'Reconectando…' : 'Conectando…'}</span></div>
      {state.status === 'loading_orders' && <LoadingState>Cargando pedidos...</LoadingState>}
      {state.orderError && <FeedbackMessage variant="error">{state.orderError}</FeedbackMessage>}
      {state.connection === 'connected' && !state.orders.length && <EmptyState title="No hay pedidos pendientes." />}
      {!!state.orders.length && <>
        <label className="first-fit-select-all"><input type="checkbox" disabled={locked || state.connection !== 'connected'}
          checked={state.selected.length === state.orders.length} onChange={e => reset(() => flow.select(e.target.checked ? state.orders.map(o => o.id_pedido) : []))} />Seleccionar todos</label>
        <ul className="first-fit-orders" aria-label="Pedidos pendientes">{state.orders.map(order => <li key={order.id_pedido}>
          <label><input type="checkbox" disabled={locked || state.connection !== 'connected'} checked={state.selected.includes(order.id_pedido)}
            onChange={e => reset(() => flow.select(e.target.checked ? [...state.selected, order.id_pedido] : state.selected.filter(id => id !== order.id_pedido)))} />
            <span><strong>#{order.id_pedido} · {order.cliente}</strong><small>{order.piezas ? `${pieceCount([order])} piezas` : 'Cantidad disponible al consultar el detalle'}</small>
              <small>{order.piezas ? detectMaterialGroups([order], adapter.resolveMaterial).groups.map(g => `${g.name} · ${g.thickness} mm`).join(' / ') : 'Material y espesor pendientes del detalle'}</small></span>
            <span className="first-fit-badge">Pendiente</span></label>
        </li>)}</ul>
      </>}
      <ActionBar><span>{state.selected.length} pedidos seleccionados</span>
        <button className="ng-button ng-button--primary" disabled={locked || !state.selected.length || state.connection !== 'connected'} onClick={() => reset(flow.prepare)}>Preparar optimización</button></ActionBar>
      {fresh > 0 && <p role="status">{fresh} nuevo pedido disponible para la siguiente ejecución.</p>}
    </section>}
    {state.error && <FeedbackMessage variant="error">{state.error}</FeedbackMessage>}
    {state.status === 'preparing' && <LoadingState>Preparando pedidos y grupos…</LoadingState>}
    {(state.selected.length > 0 || state.snapshot) && <MaterialGroupsPanel groups={state.snapshot?.groups ?? preview.groups}
      unresolved={state.snapshot ? [] : preview.unresolved} snapshot={state.snapshot} completedGroups={state.snapshot ? state.completedGroups : []} />}
    {state.snapshot && <section className="first-fit-section" aria-labelledby="groups-title">
      <h2 id="groups-title">Selección actual</h2>
      <p>Pedidos: {state.snapshot.orders.map(o => `#${o.id_pedido}`).join(', ')} · Piezas: {state.snapshot.total} · Grupos detectados: {state.snapshot.groups.length}</p>
      {state.status === 'prepared' && <ActionBar><button className="ng-button ng-button--primary" disabled={!canExecute || (adapter.isFixture && !rasterReady)} onClick={flow.run}>Ejecutar First Fit</button>
        {adapter.isFixture && !rasterReady && <p role="status">Preparación pendiente: faltan máscaras válidas de algunas piezas.</p>}</ActionBar>}
      {(state.runId || state.optimizationId) && <>
        <h2>Progreso de optimización</h2>
        {state.snapshot.fixture && <p>Simulación de etapas y rotaciones; integración del motor real pendiente.</p>}
        <ol className="first-fit-stages" aria-label="Etapas de optimización">{STAGES.map(([id, label], i) => {
          const status = state.estado === 'COMPLETADA' || i < stageIndex ? 'Completado' : i === stageIndex ? state.status === 'failed' ? 'Error' : 'Activo' : 'Pendiente';
          return <li key={id} aria-current={status === 'Activo' ? 'step' : undefined}><span>{label}</span><small>{status}</small></li>;
        })}</ol>
        {state.status === 'failed' && <p role="status">Optimización fallida</p>}
        <p role="status">{state.placed_units} / {state.total_units} piezas colocadas</p>
        <progress aria-label="Piezas colocadas" value={state.placed_units} max={state.total_units} />
        <PlacementCanvas key={state.runId} snapshot={state.snapshot} placements={state.placements} />
      </>}
      {state.estado === 'SIN_SOLUCION' && <p role="status">SIN_SOLUCION: colocaciones de diagnóstico; no se puede confirmar.</p>}
      {state.estado && <p role="status">Estado del cálculo: {state.estado}</p>}
      {state.confirmed && <p role="status">Solución ya confirmada.</p>}
      {['completed', 'no_solution'].includes(state.status) && !state.metrics_available && <p>Métricas no disponibles.</p>}
      {state.metrics_available && state.metrics && <section aria-labelledby="result-title"><h2 id="result-title">Resultado First Fit</h2>
        <dl className="optimization-facts">{[
          ['Piezas colocadas', `${state.placed_units} / ${state.total_units}`], ['Pedidos', state.snapshot.orders.length], ['Grupos/material', state.snapshot.groups.length],
          ['Planchas nuevas utilizadas', state.metrics.planchas_nuevas_usadas], ['Aprovechamiento obtenido', `${state.metrics.aprovechamiento_pct} %`],
          ['Merma', `${state.metrics.merma_mm2} mm²`], ['Retazo recuperable', `${state.metrics.retazo_recuperable_mm2} mm²`], ['Tiempo', `${state.metrics.tiempo_computacional_ms} ms`],
        ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section>}
      <ActionBar>
        <button className="ng-button" onClick={() => reset(flow.discard)}>Descartar</button>
        {canExecute && ['completed', 'failed', 'no_solution'].includes(state.status) && <button className="ng-button" onClick={() => reset(flow.run)}>Ejecutar nuevamente</button>}
        {canConfirm && state.confirmable && !state.confirmed && <button className="ng-button ng-button--primary" onClick={() => setDialog(true)}>Confirmar solución</button>}
        {state.optimizationId && adapter.loadResult && <button className="ng-button" onClick={flow.recover}>Recuperar resultado</button>}
      </ActionBar>
    </section>}
    {confirmation && <FeedbackMessage variant="info">{confirmation}</FeedbackMessage>}
    <ConfirmDialog open={dialog} title="Confirmar solución" confirmLabel="Confirmar solución" onCancel={() => setDialog(false)} onConfirm={confirm}>
      <p>Esta acción confirmará las colocaciones obtenidas mediante First Fit. El backend podrá actualizar las planchas y retazos utilizados del inventario. Esta operación puede modificar las existencias disponibles.</p>
      <p>La confirmación todavía no está conectada al backend. Esta demostración no guardará cambios ni modificará existencias.</p>
    </ConfirmDialog>
  </>;
}

function OptimizationContent({ user, result, token, source: providedSource, adapter: providedAdapter, onSessionExpired }) {
  const [demo, setDemo] = useState(false);
  const source = useMemo(() => providedSource ?? (demo ? createDemoOrdersSource() : canExecuteOptimization(user) ? createPendingOrdersSource({ token }) : createFixturePendingOrdersSource([])), [providedSource, demo, token, user]);
  const adapter = useMemo(() => providedAdapter ?? (demo ? createFixtureAdapter() : unavailableOptimizationAdapter), [providedAdapter, demo]);
  return <PageCard className="optimization-page">
    <PageHeader title="Optimización" context="Corte de vidrio · Primer ajuste" icon={ScanLine}
      description="Selecciona pedidos compatibles y visualiza las colocaciones de una solución First Fit." />
    {!providedSource && canExecuteOptimization(user) && <ActionBar><button className="ng-button" onClick={() => setDemo(value => !value)}>{demo ? 'Volver a pedidos reales' : 'Explorar demostración'}</button></ActionBar>}
    {(demo || providedAdapter?.isFixture) && <FeedbackMessage variant="warning">Demostración con datos de ejemplo. Las colocaciones y métricas son simuladas; no se modifican pedidos ni inventario.</FeedbackMessage>}
    {!demo && !providedSource && canExecuteOptimization(user) && <p>Pedidos reales: consulta automática cada 15 segundos. La ejecución First Fit está pendiente de integración backend.</p>}
    <OptimizationWorkspace key={`${demo}:${token}`} source={source} adapter={adapter} onSessionExpired={onSessionExpired} user={user} result={result} />
  </PageCard>;
}
export function OptimizationPage({ user, toolbar, initialMode = 'first-fit', ...props }) {
  const [mode, setMode] = useState(initialMode);
  return <AppShell activeItem="optimization" user={user}>{toolbar}
    {canViewResults(user) ? <>
      <div className="ng-ui"><ActionBar>
        <button className="ng-button" aria-pressed={mode === 'first-fit'} onClick={() => setMode('first-fit')}>First Fit</button>
        <button className="ng-button" aria-pressed={mode === 'hu015'} onClick={() => setMode('hu015')}>Rasterización de piezas</button>
      </ActionBar></div>
      {mode === 'first-fit' ? <OptimizationContent {...props} user={user} />
        : canExecuteOptimization(user) ? <Hu015Rasterization {...props} />
          : <FeedbackMessage variant="error">No tienes permiso para ejecutar la rasterización.</FeedbackMessage>}
    </> : <FeedbackMessage variant="error">No tienes permiso para consultar la optimización.</FeedbackMessage>}
  </AppShell>;
}
