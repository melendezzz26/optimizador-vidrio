import { useState } from 'react';
import { RunMaskInspection } from './RunMaskInspection';

export function RunVisualization({ state, adapter, onSessionExpired }) {
  const [hidden, setHidden] = useState(false);
  const [paused, setPaused] = useState(null);
  const visual = paused ?? state.visual;
  const current = visual.current;
  return <section className="first-fit-section" aria-label="Proceso visual de optimización">
    <h2>Proceso de las piezas</h2>
    <p aria-live="polite" aria-atomic="true">{state.visual.preparation === 'running' ? 'Preparando las máscaras base.'
      : state.visual.preparation === 'complete' ? 'Máscaras base preparadas.' : 'Consultando el detalle de la corrida.'}</p>
    <p>{state.visual.processed} / {state.total_units} piezas procesadas; {state.placed_units} colocadas.</p>
    {current?.id_pieza && <p>Pedido #{current.id_pedido} · Pieza #{current.id_pieza}{current.unit_index ? ` · unidad ${current.unit_index}` : ''}
      {current.source && ` · ${current.source.material_source === 'RETAZO' ? 'Retazo' : 'Plancha'} #${current.source.material_id}, unidad física ${current.source.stock_unit_index}`}
      {current.mask && ` · Giro ${current.mask.rotation_deg}°`}</p>}
    <p>Las orientaciones mostradas son muestras de evaluaciones reales. Cada colocación y cada pieza sin ubicar se conservan en el resultado.</p>
    {!!visual.order.length && <details><summary>Orden observado de las piezas</summary><ol>
      {visual.order.map(unit => <li key={`${unit.id_pedido}:${unit.id_pieza}:${unit.unit_index}`}>Pedido #{unit.id_pedido} · Pieza #{unit.id_pieza} · unidad {unit.unit_index}</li>)}
    </ol></details>}
    {current?.mask && <details><summary>Detalle de la evaluación</summary><dl className="optimization-facts">
      <div><dt>Resolución efectiva</dt><dd>{current.mask.resolution_mm} mm/celda</dd></div>
      <div><dt>Dimensiones raster</dt><dd>{current.mask.columns} × {current.mask.row_count}</dd></div>
      {current.evaluation_index && <div><dt>Ordinal de la evaluación</dt><dd>{current.evaluation_index}</dd></div>}
      {current.score !== null && current.score !== undefined && <div><dt>Capacidad libre posterior</dt><dd>{current.score} celdas</dd></div>}
    </dl></details>}
    <div className="optimization-actions">
      <button type="button" className="ng-button" aria-pressed={paused !== null} onClick={() => setPaused(value => value ? null : state.visual)}>{paused ? 'Reanudar vista' : 'Pausar vista'}</button>
      <button type="button" className="ng-button" aria-expanded={!hidden} onClick={() => setHidden(value => !value)}>{hidden ? 'Mostrar detalle visual' : 'Ocultar detalle visual'}</button>
    </div>
    {paused && <p role="status">Vista pausada; el cálculo y su recepción continúan.</p>}
    {!hidden && <RunMaskInspection runId={state.optimizationId} adapter={adapter} visual={visual}
      preferredPlacement={state.placements?.at(-1)} onSessionExpired={onSessionExpired} />}
  </section>;
}
