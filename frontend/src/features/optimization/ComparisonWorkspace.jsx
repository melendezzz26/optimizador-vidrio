// Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
import { useEffect, useId, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import { canExecuteOptimization, hasPermission } from '../authentication';
import { PageCard } from '../../shared/components/PageLayout';
import { ConfirmDialog, FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import { createPendingOrdersSource } from './pendingOrdersSource';
import { createComparisonApi, METHODS, METHOD_NAMES } from './comparisonApi';
import { createComparisonController } from './comparisonController';
import { resultSnapshot, visualPlacement } from './runContract';
import { GeometryPreview } from './GeometryPreview';
import { getGeometryBounds, getRasterComparisonFrame } from './visualizationGeometry';
import { PlacementCanvas } from './PlacementCanvas';
import { RunMaskInspection } from './RunMaskInspection';
import './ComparisonWorkspace.css';

const PHASES = ['Máscaras', 'Orden de piezas', 'Giros y colocación', 'Resultado'];
const metricRows = [['aprovechamiento_pct', 'Aprovechamiento', '%'], ['merma_mm2', 'Merma', 'mm²'],
  ['retazo_recuperable_mm2', 'Retazo recuperable', 'mm²'], ['planchas_nuevas_usadas', 'Planchas nuevas', ''], ['tiempo_computacional_ms', 'Tiempo de cálculo', 'ms']];
const status = e => e.status === 'FALLIDA' ? 'Falló' : e.status === 'EN_EJECUCION' ? 'En ejecución' : e.complete ? 'Completo' : 'Con piezas sin colocar';
const failure = code => ({ MEMORY_BUDGET_EXCEEDED: 'El motor alcanzó su límite de memoria.', TIME_BUDGET_EXCEEDED: 'El motor superó el tiempo de cálculo.',
  RESULT_SAVE_FAILED: 'No se pudo guardar el resultado de este motor.', WORKER_STOPPED: 'El proceso se interrumpió.', PROCESS_START_FAILED: 'No se pudo iniciar el proceso.' })[code] ?? 'Este motor no pudo completar su ejecución.';

function readOnlySource() {
  let listener;
  return { subscribe(fn) { listener = fn; return () => { listener = null; }; },
    load() { listener?.({ type: 'orders', orders: [] }); }, dispose() {}, refresh() {} };
}

function OriginalRequest({ comparison }) {
  return <details className="comparison-request"><summary>Piezas y medidas solicitadas <span>{comparison.requested_pieces.reduce((n, p) => n + p.cantidad, 0)} unidades</span></summary>
    <div className="comparison-request-grid">{comparison.requested_pieces.map(p => <article key={p.id_pieza}>
      <h3>Pedido #{p.id_pedido} · Pieza #{p.id_pieza}</h3>
      <p>{p.cantidad} unidades · {p.material_nombre ?? `Vidrio #${p.id_tipo_vidrio}`} · espesor {p.espesor_mm} mm</p>
      <GeometryPreview geometry={p.geometria} pieceId={p.id_pieza} frame={getRasterComparisonFrame(p.geometria)} />
      <p>{p.dimensiones ? 'Medidas guardadas del pedido' : 'Medidas derivadas de la geometría guardada'}</p>
      {p.dimensiones && <dl>{Object.entries(p.dimensiones).map(([key, value]) => <div key={key}>
        <dt>{({ width_mm: 'Ancho', height_mm: 'Alto', radius_mm: 'Radio', vertices_mm: 'Vértices', lengths_mm: 'Longitudes', angles_deg: 'Ángulos' })[key] ?? key.replaceAll('_', ' ')}</dt>
        <dd>{Array.isArray(value) ? value.map(v => Array.isArray(v) ? `(${v.join(', ')})` : String(v)).join(' · ') : String(value)}{key.endsWith('_mm') ? ' mm' : key.endsWith('_deg') ? '°' : ''}</dd>
      </div>)}</dl>}
      <small>Estas medidas corresponden a la solicitud original; las colocaciones pueden estar giradas.</small>
    </article>)}</div>
  </details>;
}

function TurningPiece({ piece, angle }) {
  const [shown, setShown] = useState(0);
  useEffect(() => { const frame = requestAnimationFrame(() => setShown(Number(angle))); return () => cancelAnimationFrame(frame); }, [angle]);
  const bounds = getGeometryBounds(piece.geometria);
  const size = Math.hypot(bounds.width, bounds.height) * 1.3;
  const geometry = piece.geometria;
  return <div className="comparison-turn"><svg viewBox={`${-size / 2} ${-size / 2} ${size} ${size}`} role="img" aria-label={`Giro real de la pieza #${piece.id_pieza}: ${Number(angle)} grados`}>
    <g className="comparison-turning-shape" style={{ transform: `rotate(${shown}deg)` }}>
      <g transform={`translate(${-bounds.minX - bounds.width / 2} ${-bounds.minY - bounds.height / 2})`}>
        {geometry.type === 'RECTANGULO' ? <rect width={geometry.width_mm} height={geometry.height_mm} />
          : geometry.type === 'CIRCUNFERENCIA' ? <circle r={geometry.radius_mm} /> : <polygon points={geometry.vertices_mm.map(p => p.join(',')).join(' ')} />}
      </g>
    </g></svg><p>Pieza #{piece.id_pieza} · giro recibido <strong>{Number(angle)}°</strong></p>
    <small>Se muestran muestras de giros reales. La animación acompaña los ángulos recibidos.</small></div>;
}

function liveSnapshot(comparison, live) {
  const groups = new Map();
  comparison.requested_pieces.forEach(p => {
    const key = `${p.id_tipo_vidrio}:${Number(p.espesor_mm)}`;
    if (!groups.has(key)) groups.set(key, { id_tipo_vidrio: p.id_tipo_vidrio, espesor_mm: p.espesor_mm, units: [] });
    for (let i = 1; i <= p.cantidad; i++) groups.get(key).units.push({ ...p, unit_index: i });
  });
  return resultSnapshot({ order_ids: comparison.order_ids, total_units: comparison.executions[0].total_units,
    groups: [...groups.values()], materials_used: live?.materials ?? [], residual_regions: [] });
}

function EnginePanel({ comparison, execution, visual: supplied, live, result, api, onSessionExpired }) {
  const visual = supplied ?? { descriptors: {}, current: null, order: [], processed: 0 };
  const [presented, setPresented] = useState(0), [inspection, setInspection] = useState(null), [paused, setPaused] = useState(null);
  const masks = Object.values(visual.descriptors).filter(m => m.kind === 'PIECE' && Number(m.rotation_deg) === 0);
  const hasMasks = masks.length > 0, hasOrder = visual.order.length > 0;
  const hasTurn = !!visual.lastOrientation?.mask || !!live?.placements.length, hasResult = !!result;
  const available = useMemo(() => [hasMasks, hasOrder, hasTurn, hasResult], [hasMasks, hasOrder, hasTurn, hasResult]);
  const target = hasResult ? 3 : hasTurn ? 2 : hasOrder ? 1 : 0;
  useEffect(() => {
    if (presented >= target) return undefined;
    const next = [1, 2, 3].find(i => i > presented && i <= target && available[i]);
    if (next === undefined) return undefined;
    const reduced = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const timer = setTimeout(() => setPresented(next), reduced ? 0 : 550);
    return () => clearTimeout(timer);
  }, [presented, target, available]);
  const phase = paused?.phase ?? inspection ?? presented;
  const shownVisual = paused?.visual ?? visual;
  const shownMasks = Object.values(shownVisual.descriptors).filter(m => m.kind === 'PIECE' && Number(m.rotation_deg) === 0);
  const base = shownMasks[0];
  const preparation = { ...shownVisual, descriptors: Object.fromEntries(shownMasks.map(m => [m.mask_ref, m])),
    current: base ? { ...base.piece, mask: base } : null };
  const executionId = execution.execution_id, method = execution.method;
  const adapter = useMemo(() => api.forExecution(comparison.comparison_id, { execution_id: executionId, method }), [api, comparison.comparison_id, executionId, method]);
  const current = shownVisual.lastOrientation ?? shownVisual.current;
  const piece = comparison.requested_pieces.find(p => p.id_pieza === current?.id_pieza);
  const snapshot = result ? resultSnapshot(result) : liveSnapshot(comparison, live);
  const placements = result ? result.placements.map(visualPlacement) : live?.placements ?? [];
  snapshot.groups = snapshot.groups.map(g => ({ ...g, name: comparison.requested_pieces.find(p => p.id_tipo_vidrio === g.materialId)?.material_nombre ?? g.name }));
  const viewSnapshot = paused?.snapshot ?? snapshot, viewPlacements = paused?.placements ?? placements;
  const currentPlacement = viewPlacements.find(p => p.id_pieza === current?.id_pieza && p.unit_index === current?.unit_index);
  const unavailableGroups = result?.groups?.filter(group => group.stock_compatible === false) ?? [];
  const placed = result?.placed_units ?? (execution.status === 'COMPLETADA' ? execution.placed_units
    : visual.current?.placed_units ?? visual.lastOrientation?.placed_units ?? live?.placements.length ?? 0);
  const processed = execution.status === 'COMPLETADA' ? execution.total_units : visual.processed ?? 0;
  return <section className="comparison-engine" aria-label={`Ejecución ${METHOD_NAMES[execution.method]}`}>
    <header><div><span className="comparison-eyebrow">Motor {execution.method}</span><h2>{METHOD_NAMES[execution.method]}</h2></div>
      <span className={`comparison-status ${execution.status === 'FALLIDA' ? 'is-failed' : ''}`}>{status(execution)}</span></header>
    {execution.status === 'FALLIDA' && <FeedbackMessage variant="error">{failure(execution.failure_code)}</FeedbackMessage>}
    {execution.status !== 'FALLIDA' && <div className="comparison-progress"><p role="status">{placed} / {execution.total_units} piezas colocadas · {processed} procesadas</p>
      <progress aria-label={`Piezas colocadas por ${METHOD_NAMES[execution.method]}`} value={placed} max={execution.total_units} /></div>}
    <ol className="comparison-phases" aria-label="Fases del motor">{PHASES.map((label, index) => <li key={label}>
      <button type="button" aria-current={phase === index ? 'step' : undefined} disabled={!available[index] && index !== 0}
        onClick={() => { setInspection(index); setPaused(null); }}><span>{index + 1}</span>{label}</button>
    </li>)}</ol>
    <div className="comparison-phase-tools"><p role="status">{execution.status !== 'EN_EJECUCION' && phase < 3 ? 'Cálculo terminado · mostrando pasos observados' : PHASES[phase]}</p>
      <button type="button" className="ng-button" onClick={() => setPaused(value => value ? null : { phase, visual, snapshot, placements })}>{paused ? 'Reanudar vista' : 'Pausar vista'}</button>
      {inspection !== null && <button type="button" className="ng-button" onClick={() => { setInspection(null); setPaused(null); }}>Seguir avance</button>}</div>
    {paused && <p role="status">Vista pausada; los motores y la recepción de resultados continúan.</p>}
    <div className="comparison-phase-body" data-phase={phase}>
      {phase === 0 && <><h3>Máscaras de las piezas</h3><p>Representación raster utilizada por este motor.</p>
        <RunMaskInspection runId={comparison.comparison_id} adapter={adapter} visual={preparation} onSessionExpired={onSessionExpired} /></>}
      {phase === 1 && <><h3>Orden de procesamiento</h3><p>Primero mayor área y lado mayor; los empates siguen pedido, pieza y unidad. Este es el orden calculado por el motor.</p>
        <ol className="comparison-order">{shownVisual.order.map(u => <li key={`${u.id_pieza}:${u.unit_index}`}>Pedido #{u.id_pedido} · Pieza #{u.id_pieza} · unidad {u.unit_index}</li>)}</ol></>}
      {phase === 2 && <><h3>Giros y colocación</h3>{piece && current?.mask && <TurningPiece key={piece.id_pieza} piece={piece} angle={current.mask.rotation_deg} />}
        {current?.source && <p>{current.kind === 'source_selected' ? 'Material seleccionado' : 'Material evaluado'}: {current.source.material_source === 'PLANCHA' ? 'plancha' : 'retazo'} #{current.source.material_id}, unidad {current.source.stock_unit_index}.</p>}
        {currentPlacement && <p>Posición aplicada: x {currentPlacement.x_mm} mm · y {currentPlacement.y_mm} mm.</p>}
        <RunMaskInspection runId={comparison.comparison_id} adapter={adapter} visual={{ ...shownVisual, current }} onSessionExpired={onSessionExpired} />
        {!!viewPlacements.length && <PlacementCanvas snapshot={viewSnapshot} placements={viewPlacements} />}</>}
      {phase === 3 && result && <><h3>Resultado de {METHOD_NAMES[execution.method]}</h3><p>{result.placed_units} / {result.total_units} piezas colocadas</p>
        {!!unavailableGroups.length && <FeedbackMessage variant="warning">
          No hay planchas ni retazos compatibles para {unavailableGroups.map(group =>
            `material #${group.id_tipo_vidrio}, espesor ${group.espesor_mm} mm`).join('; ')}.
        </FeedbackMessage>}
        <Metrics metrics={execution.metrics} />{!result.completo && <p role="status">Hay piezas sin colocar; este resultado no puede confirmarse.</p>}
        {!!result.unplaced_units.length && <ul aria-label="Piezas sin colocar">{result.unplaced_units.map(p => <li key={`${p.id_pieza}:${p.unit_index}`}>Pedido #{p.id_pedido} · Pieza #{p.id_pieza} · unidad {p.unit_index}</li>)}</ul>}
        <PlacementCanvas snapshot={viewSnapshot} placements={viewPlacements} visualContext={{ visual, runId: comparison.comparison_id, adapter }} /></>}
    </div>
  </section>;
}

function Metrics({ metrics }) {
  return metrics ? <dl className="comparison-metrics">{metricRows.map(([key, label, unit]) => <div key={key}><dt>{label}</dt><dd>{metrics[key]} <small>{unit}</small></dd></div>)}</dl>
    : <p>Las métricas estarán disponibles al guardar un resultado con piezas colocadas.</p>;
}

export function ComparisonWorkspace({ token, user, initialRunId, onSessionExpired, onLegacy, comparisonAdapter, source: suppliedSource }) {
  const execute = canExecuteOptimization(user), canConfirm = hasPermission(user, 'optimization.confirm');
  const api = useMemo(() => comparisonAdapter ?? createComparisonApi({ token }), [comparisonAdapter, token]);
  const source = useMemo(() => suppliedSource ?? (execute ? createPendingOrdersSource({ token }) : readOnlySource()), [suppliedSource, execute, token]);
  const storageKey = `newglass:comparison:${user.id_usuario ?? user.user_id ?? user.usuario}`;
  const flow = useMemo(() => createComparisonController({ api, source, storageKey, initialId: initialRunId,
    onExpired: onSessionExpired, onLegacy }), [api, source, storageKey, initialRunId, onSessionExpired, onLegacy]);
  const state = useSyncExternalStore(flow.subscribe, flow.getSnapshot, flow.getSnapshot);
  useEffect(() => { flow.mount(); return () => flow.dispose(); }, [flow]);
  return <ComparisonView key={state.comparison?.comparison_id ?? 'pending'} state={state} flow={flow}
    api={api} execute={execute} canConfirm={canConfirm} onSessionExpired={onSessionExpired} />;
}

function ComparisonView({ state, flow, api, execute, canConfirm, onSessionExpired }) {
  const [tab, setTab] = useState('FF'), [lookup, setLookup] = useState(''), [dialog, setDialog] = useState(false);
  const pendingHeading = useRef(null);
  const id = useId(), current = state.comparison;
  useEffect(() => {
    if (!current && state.success) {
      pendingHeading.current?.focus({ preventScroll: true });
      pendingHeading.current?.closest('.comparison-workspace')?.scrollIntoView?.({ block: 'start' });
    }
  }, [current, state.success]);
  const selected = current?.executions.find(e => e.execution_id === current.selected_execution_id);
  const tabs = [...METHODS, 'comparison'];
  const locked = state.busy || current && !current.released && !current.confirmed;
  return <PageCard className="comparison-workspace">
    <header className="comparison-heading"><div><span className="comparison-eyebrow">Tres motores · una misma solicitud</span><h2>Comparar distribuciones de corte</h2>
      <p>Revisa el proceso de cada motor, compara sus métricas y elige una distribución.</p></div>
      {current && <div className="comparison-job">Trabajo <strong>#{current.comparison_id}</strong><small>{current.confirmed ? 'Corte confirmado' : current.released ? 'Pedidos liberados' : current.terminal ? 'Comparación finalizada' : 'Comparación en curso'}</small>{selected && <small>Elegido: {METHOD_NAMES[selected.method]}</small>}</div>}</header>
    {state.error && <FeedbackMessage variant="error">{state.error}</FeedbackMessage>}
    {state.success && <FeedbackMessage variant="success">{state.success}</FeedbackMessage>}
    <div className="comparison-toolbar"><form onSubmit={e => { e.preventDefault(); if (Number(lookup) > 0) flow.load(Number(lookup)); }}>
      <label>Consultar trabajo guardado<input className="ng-control" type="number" min="1" value={lookup} onChange={e => setLookup(e.target.value)} /></label>
      <button className="ng-button" disabled={state.busy || !Number.isSafeInteger(Number(lookup)) || Number(lookup) <= 0}>Consultar</button></form>
      <button className="ng-button" disabled={state.busy} onClick={flow.refresh}>Recuperar estado</button></div>
    {state.loading && <LoadingState>Consultando pedidos y trabajo guardado…</LoadingState>}
    {execute && (!current || current.released || current.confirmed) && <section className="comparison-pending" aria-label="Seleccionar pedidos">
      <h3 ref={pendingHeading} tabIndex={-1}>Pedidos pendientes</h3><p>Las existencias se descuentan al confirmar la distribución que elijas.</p>
      {!state.orders.length && <p>No hay pedidos pendientes.</p>}
      <div className="comparison-pending-list">{state.orders.map(order => <label key={order.id_pedido}>
        <input type="checkbox" disabled={!!locked} checked={state.selected.includes(order.id_pedido)} onChange={e => flow.select(e.target.checked
          ? [...state.selected, order.id_pedido] : state.selected.filter(i => i !== order.id_pedido))} />
        <span><strong>Pedido #{order.id_pedido}</strong><small>{order.cliente}</small></span></label>)}</div>
      <button className="ng-button ng-button--primary" disabled={!!locked || !state.selected.length} onClick={flow.start}>Comparar con los tres motores</button>
    </section>}
    {current && <>
      <OriginalRequest comparison={current} />
      <details className="comparison-configuration"><summary>Configuración y unidades aplicadas</summary><p>Resolución {current.configuration.resolucion_raster_mm} mm/celda · margen {current.configuration.margen_mm} mm · separación {current.configuration.separacion_mm} mm · paso angular {current.configuration.paso_angular_grados}°.</p></details>
      {state.partial && <FeedbackMessage variant="info">Se recuperó el estado actual. Parte del avance anterior ya no estaba retenido; los resultados guardados se conservan.</FeedbackMessage>}
      {state.connection === 'reconnecting' && !current.terminal && <p role="status">Recuperando el avance; los motores continúan ejecutándose.</p>}
      <div className="comparison-tabs" role="tablist" aria-label="Motores y comparación">{tabs.map((key, index) => <button key={key} type="button" role="tab"
        id={`${id}-tab-${key}`} aria-selected={tab === key} aria-controls={`${id}-panel-${key}`} tabIndex={tab === key ? 0 : -1}
        onClick={() => setTab(key)} onKeyDown={e => {
          const next = e.key === 'ArrowRight' ? (index + 1) % 4 : e.key === 'ArrowLeft' ? (index + 3) % 4 : e.key === 'Home' ? 0 : e.key === 'End' ? 3 : null;
          if (next !== null) { e.preventDefault(); setTab(tabs[next]); document.getElementById(`${id}-tab-${tabs[next]}`)?.focus(); }
        }}>{key === 'comparison' ? 'Comparación' : METHOD_NAMES[key]}{key !== 'comparison' && <small>{status(current.executions.find(e => e.method === key))}</small>}</button>)}</div>
      {current.executions.map(execution => <div className="comparison-panel" key={execution.execution_id} role="tabpanel" id={`${id}-panel-${execution.method}`}
        aria-labelledby={`${id}-tab-${execution.method}`} hidden={tab !== execution.method}>
        <EnginePanel comparison={current} execution={execution} visual={state.visuals[execution.execution_id]} live={state.live[execution.execution_id]}
          result={state.results[execution.execution_id]?.result} api={api} onSessionExpired={onSessionExpired} />
      </div>)}
      <section className="comparison-panel comparison-results" role="tabpanel" id={`${id}-panel-comparison`} aria-labelledby={`${id}-tab-comparison`} hidden={tab !== 'comparison'}>
        <h2>Comparación de resultados</h2><p>Los tres motores usaron la misma solicitud, configuración e inventario inicial. La elección es tuya.</p>
        {current.incomplete && <FeedbackMessage variant="warning">La comparación está incompleta porque falló un motor. Al finalizar los tres procesos puedes elegir un resultado completo guardado.</FeedbackMessage>}
        <p className="comparison-table-hint">Desliza horizontalmente para consultar todas las métricas.</p>
        <div className="comparison-table-scroll" role="region" aria-label="Tabla comparativa con desplazamiento horizontal" tabIndex={0}><table><caption>Métricas de los tres motores</caption><thead><tr><th>Motor</th><th>Estado</th><th>Piezas</th>{metricRows.map(([, label, unit]) => <th key={label}>{label}{unit && <small>{unit}</small>}</th>)}<th>Elegir</th></tr></thead>
          <tbody>{current.executions.map(execution => <tr key={execution.execution_id} className={current.selected_execution_id === execution.execution_id ? 'is-selected' : ''}>
            <th scope="row">{METHOD_NAMES[execution.method]}</th><td>{status(execution)}</td><td>{execution.status === 'FALLIDA' ? '—' : execution.status === 'EN_EJECUCION' ? 'En proceso' : `${execution.placed_units} / ${execution.total_units}`}</td>
            {metricRows.map(([key]) => <td key={key}>{execution.metrics?.[key] ?? '—'}</td>)}
            <td><label><input type="radio" name={`${id}-engine`} aria-label={`Elegir ${METHOD_NAMES[execution.method]}`}
              checked={current.selected_execution_id === execution.execution_id} disabled={!execute || state.busy || !current.selection_allowed || !execution.eligible}
              onChange={() => flow.choose(execution.execution_id)} />{current.selected_execution_id === execution.execution_id ? 'Elegido' : 'Elegir'}</label></td>
          </tr>)}</tbody></table></div>
        {!current.terminal && <p role="status">La elección se habilita cuando terminan los tres procesos y sus resultados están guardados.</p>}
        <div className="comparison-choice"><div><strong>{selected ? `${METHOD_NAMES[selected.method]} seleccionado` : 'Todavía no has elegido un motor'}</strong>
          <p>{current.confirmed ? 'El inventario y los pedidos reflejan únicamente la distribución elegida.' : 'Elegir un motor conserva el inventario. Confirma cuando hayas revisado su distribución.'}</p></div>
          {canConfirm && <button className="ng-button ng-button--primary" disabled={state.busy || !current.confirmable} onClick={() => setDialog(true)}>{state.busy ? 'Procesando…' : 'Confirmar distribución elegida'}</button>}
        </div>
      </section>
      <footer className="comparison-footer">
        {execute && current.terminal && !current.confirmed && !current.released && <button className="ng-button" disabled={state.busy} onClick={flow.release}>Liberar pedidos sin confirmar</button>}
        {(current.confirmed || current.released) && <button className="ng-button" onClick={flow.reset}>Preparar otro trabajo</button>}
        <p>{current.confirmed ? 'Confirmado' : current.released ? 'Liberado' : current.terminal ? 'Resultados guardados' : 'Cálculo en curso'} · Trabajo #{current.comparison_id}</p>
      </footer>
    </>}
    <ConfirmDialog open={dialog} title={`Confirmar ${selected ? METHOD_NAMES[selected.method] : 'distribución'}`} confirmLabel="Confirmar corte"
      onCancel={() => setDialog(false)} onConfirm={() => { setDialog(false); flow.confirm(); }}>
      <p>Se descontarán únicamente las planchas y retazos de {selected ? METHOD_NAMES[selected.method] : 'la distribución elegida'} y se confirmarán sus pedidos.</p>
    </ConfirmDialog>
  </PageCard>;
}
