import { useMemo, useState } from 'react';
import { ScanLine } from 'lucide-react';
import { canExecuteOptimization } from '../authentication';
import { AppShell } from '../../shared/components/AppShell';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import { ConfirmDialog, EmptyState, FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import { createPendingOrdersSource } from './pendingOrdersSource';
import { createDemoOrdersSource, createFixtureAdapter, unavailableOptimizationAdapter } from './firstFitFixture';
import { STAGES, pieceCount } from './optimizationModel';
import { useFirstFit } from './useFirstFit';
import { PlacementCanvas } from './PlacementCanvas';
import { RasterComparison } from './RasterComparison';
import './OptimizationPage.css';

function OptimizationWorkspace({ source, adapter, onSessionExpired }) {
  const flow = useFirstFit({ source, adapter, onSessionExpired });
  const { state } = flow;
  const [dialog, setDialog] = useState(false);
  const [confirmation, setConfirmation] = useState('');
  const locked = ['preparing', 'running'].includes(state.status);
  const fresh = state.runId ? state.orders.filter(o => !state.availableAtStart?.includes(o.id_pedido)).length : 0;
  const stageIndex = STAGES.findIndex(([id]) => id === state.stage);
  const rasterPiece = state.snapshot?.orders.flatMap(o => o.piezas).find(p => state.snapshot.rasters?.[p.id_pieza]);
  async function confirm() {
    setDialog(false);
    try {
      await adapter.confirm(state);
      setConfirmation('Solución confirmada por el servidor.');
    } catch (error) { setConfirmation(error.message); }
  }
  function reset(action) { setConfirmation(''); action(); }
  return <>
    <section aria-labelledby="pending-orders-title">
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
            <span><strong>#{order.id_pedido} · {order.cliente}</strong><small>{order.piezas ? `${pieceCount([order])} piezas` : 'Cantidad disponible al consultar el detalle'}</small></span>
            <span className="first-fit-badge">Pendiente</span></label>
        </li>)}</ul>
      </>}
      <ActionBar><span>{state.selected.length} pedidos seleccionados</span>
        <button className="ng-button ng-button--primary" disabled={locked || !state.selected.length || state.connection !== 'connected'} onClick={() => reset(flow.prepare)}>Preparar optimización</button></ActionBar>
      {fresh > 0 && <p role="status">{fresh} nuevo pedido disponible para la siguiente ejecución.</p>}
    </section>
    {state.error && <FeedbackMessage variant="error">{state.error}</FeedbackMessage>}
    {state.status === 'preparing' && <LoadingState>Preparando pedidos y grupos…</LoadingState>}
    {state.snapshot && <section className="first-fit-section" aria-labelledby="groups-title">
      <h2 id="groups-title">Selección actual</h2>
      <p>Pedidos: {state.snapshot.orders.map(o => `#${o.id_pedido}`).join(', ')} · Piezas: {state.snapshot.total} · Grupos detectados: {state.snapshot.groups.length}</p>
      <ul className="first-fit-groups">{state.snapshot.groups.map(g => <li key={g.id}><strong>{g.name} · {g.thickness} mm</strong>
        <span>{g.units.length} piezas · pedidos {g.orders.map(id => `#${id}`).join(', ')}</span>
        {state.completedGroups.includes(g.id) && <span>Completado</span>}</li>)}</ul>
      {state.status === 'prepared' && <ActionBar><button className="ng-button ng-button--primary" onClick={flow.run}>Ejecutar First Fit</button></ActionBar>}
      {state.runId && <>
        <ol className="first-fit-stages" aria-label="Etapas de optimización">{STAGES.map(([id, label], i) => {
          const status = state.status === 'completed' || i < stageIndex ? 'Completado' : i === stageIndex ? state.status === 'failed' ? 'Error' : 'Activo' : 'Pendiente';
          return <li key={id} aria-current={status === 'Activo' ? 'step' : undefined}><span>{label}</span><small>{status}</small></li>;
        })}</ol>
        <p role="status">{state.placements.length} / {state.snapshot.total} piezas colocadas</p>
        <progress aria-label="Piezas colocadas" value={state.placements.length} max={state.snapshot.total} />
        <PlacementCanvas key={state.runId} snapshot={state.snapshot} placements={state.placements} />
        {rasterPiece && <details><summary>Inspeccionar geometría y raster de ejemplo · pieza #{rasterPiece.id_pieza}</summary>
          <RasterComparison geometry={rasterPiece.geometria} piece={rasterPiece} raster={{ ...state.snapshot.rasters[rasterPiece.id_pieza], tipo_forma: rasterPiece.tipo_forma, cantidad: rasterPiece.cantidad }} />
        </details>}
      </>}
      {state.metrics && <section aria-labelledby="result-title"><h2 id="result-title">Resultado First Fit</h2>
        <dl className="optimization-facts">{[
          ['Piezas colocadas', `${state.metrics.placed} / ${state.metrics.total}`], ['Pedidos', state.metrics.orders], ['Grupos/material', state.metrics.groups],
          ['Retazos utilizados', state.metrics.remnants], ['Planchas utilizadas', state.metrics.sheets], ['Aprovechamiento obtenido', `${state.metrics.utilization} %`],
          ['Merma', `${state.metrics.waste} %`], ['Tiempo', `${state.metrics.duration_ms} ms`],
        ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section>}
      <ActionBar>
        <button className="ng-button" onClick={() => reset(flow.discard)}>Descartar</button>
        {['completed', 'failed'].includes(state.status) && <button className="ng-button" onClick={() => reset(flow.run)}>Ejecutar nuevamente</button>}
        {state.status === 'completed' && <button className="ng-button ng-button--primary" onClick={() => setDialog(true)}>Confirmar solución</button>}
      </ActionBar>
    </section>}
    {confirmation && <FeedbackMessage variant="info">{confirmation}</FeedbackMessage>}
    <ConfirmDialog open={dialog} title="Confirmar solución" confirmLabel="Confirmar solución" onCancel={() => setDialog(false)} onConfirm={confirm}>
      <p>Esta acción confirmará las colocaciones obtenidas mediante First Fit. El backend podrá actualizar las planchas y retazos utilizados del inventario. Esta operación puede modificar las existencias disponibles.</p>
      <p>La confirmación todavía no está conectada al backend. Esta demostración no guardará cambios ni modificará existencias.</p>
    </ConfirmDialog>
  </>;
}

function OptimizationContent({ token, source: providedSource, adapter: providedAdapter, onSessionExpired }) {
  const [demo, setDemo] = useState(false);
  const source = useMemo(() => providedSource ?? (demo ? createDemoOrdersSource() : createPendingOrdersSource({ token })), [providedSource, demo, token]);
  const adapter = useMemo(() => providedAdapter ?? (demo ? createFixtureAdapter() : unavailableOptimizationAdapter), [providedAdapter, demo]);
  return <PageCard className="optimization-page">
    <PageHeader title="Optimización" context="Corte de vidrio · Primer ajuste" icon={ScanLine}
      description="Selecciona pedidos compatibles y visualiza las colocaciones de una solución First Fit." />
    {!providedSource && <ActionBar><button className="ng-button" onClick={() => setDemo(value => !value)}>{demo ? 'Volver a pedidos reales' : 'Explorar demostración'}</button></ActionBar>}
    {(demo || providedAdapter?.isFixture) && <FeedbackMessage variant="warning">Demostración con datos de ejemplo. Las colocaciones y métricas son simuladas; no se modifican pedidos ni inventario.</FeedbackMessage>}
    {!demo && !providedSource && <p>Pedidos reales: consulta automática cada 15 segundos. La ejecución First Fit está pendiente de integración backend.</p>}
    <OptimizationWorkspace key={`${demo}:${token}`} source={source} adapter={adapter} onSessionExpired={onSessionExpired} />
  </PageCard>;
}
export function OptimizationPage({ user, toolbar, ...props }) {
  return <AppShell activeItem="optimization" user={user}>{toolbar}
    {canExecuteOptimization(user) ? <OptimizationContent {...props} /> : <FeedbackMessage variant="error">No tienes permiso para ejecutar la optimización.</FeedbackMessage>}
  </AppShell>;
}
