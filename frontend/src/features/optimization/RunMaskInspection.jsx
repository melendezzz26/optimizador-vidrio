import { useEffect, useId, useRef, useState } from 'react';
import { GeometryPreview } from './GeometryPreview';
import { RasterPreview } from './RasterPreview';
import { getRasterComparisonFrame } from './visualizationGeometry';

export function RunMaskInspection({ runId, adapter, visual, group, placements, preferredPlacement, onSessionExpired }) {
  const id = useId();
  const [choice, setChoice] = useState(null);
  const [viewport, setViewport] = useState({ reference: null, row: 0, column: 0 });
  const [attempt, setAttempt] = useState(0);
  const [loaded, setLoaded] = useState({ key: '', value: null, error: '' });
  const last = useRef(null);
  const options = Object.values(visual.descriptors).filter(item => item.kind === 'PIECE'
    && (!group || group.units.some(unit => unit.id_pedido === item.piece.id_pedido && unit.id_pieza === item.piece.id_pieza))
    && (!placements?.length || placements.some(unit => unit.id_pedido === item.piece.id_pedido
      && unit.id_pieza === item.piece.id_pieza && Number(unit.rotation_deg) === Number(item.rotation_deg))));
  const current = visual.current?.mask;
  const preferred = visual.current?.id_pieza ? visual.current : preferredPlacement;
  const currentUnavailable = choice === null && current?.available === false;
  const selected = currentUnavailable ? undefined : options.find(item => item.mask_ref === choice)
    ?? (choice === null && (options.find(item => item.mask_ref === current?.mask_ref)
      ?? options.find(item => item.piece.id_pedido === preferred?.id_pedido && item.piece.id_pieza === preferred?.id_pieza
        && Number(item.rotation_deg) === Number(preferred?.rotation_deg ?? 0)))) ?? options[0];
  const row = viewport.reference === selected?.mask_ref ? viewport.row : 0;
  const column = viewport.reference === selected?.mask_ref ? viewport.column : 0;
  const key = selected ? `${runId}:${selected.mask_ref}:${row}:${column}:${attempt}` : '';
  useEffect(() => {
    if (!selected || !runId || !adapter.loadVisualMask) return undefined;
    const controller = new AbortController();
    if (last.current?.key === key) {
      Promise.resolve(last.current).then(value => { if (!controller.signal.aborted) setLoaded(value); });
      return () => controller.abort();
    }
    const frameId = requestAnimationFrame(() => adapter.loadVisualMask(runId, selected, { row_start: row, column_start: column,
      row_count: Math.min(256, selected.row_count - row), column_count: Math.min(1024, selected.columns - column),
      signal: controller.signal }).then(value => {
      if (!controller.signal.aborted) {
        last.current = { key, value, error: '' }; setLoaded(last.current);
      }
    }).catch(error => {
      if (controller.signal.aborted) return;
      if (error.status === 401) onSessionExpired?.();
      setLoaded({ key, value: null, error: error.status === 410
        ? 'La máscara ya no está disponible. El resultado guardado se conserva.' : error.message });
    }));
    return () => { cancelAnimationFrame(frameId); controller.abort(); };
  }, [adapter, runId, selected, row, column, key, onSessionExpired]);
  const shown = loaded.key === key ? loaded : null;
  const mask = shown?.value;
  let raster, frame;
  if (mask) {
    const w = mask.window;
    const resolution = Number(mask.resolution_mm);
    raster = { ...mask, resolution_mm: resolution, columns: w.column_count, row_count: w.row_count,
      tipo_forma: mask.geometria.type, cantidad: 1,
      spans_by_row: mask.spans_by_row.map(row => ({ row: row.row - w.row_start,
        runs: row.runs.map(([start, end]) => [start - w.column_start, end - w.column_start]) })) };
    raster.occupied_cells = raster.spans_by_row.reduce((sum, row) => sum + row.runs.reduce((n, [start, end]) => n + end - start, 0), 0);
    frame = getRasterComparisonFrame({ type: 'RECTANGULO', width_mm: w.column_count * resolution, height_mm: w.row_count * resolution });
  }
  function shift(deltaRow, deltaColumn) {
    setViewport({ reference: selected.mask_ref,
      row: Math.max(0, Math.min(selected.row_count - 1, row + deltaRow)),
      column: Math.max(0, Math.min(selected.columns - 1, column + deltaColumn)) });
  }
  return <section className="run-mask-inspection" aria-labelledby={`${id}-title`}>
    <h3 id={`${id}-title`}>Máscara real de la corrida</h3>
    {!selected ? <p role="status">{visual.error || (currentUnavailable
      ? 'La máscara de esta orientación excedió el presupuesto visual. El cálculo y el resultado se conservan.'
      : 'La máscara estará disponible cuando el servidor prepare la pieza.')}</p> : <>
      <label htmlFor={`${id}-follow`}><input id={`${id}-follow`} type="checkbox" checked={choice === null}
        onChange={event => setChoice(event.target.checked ? null : selected.mask_ref)} />Seguir pieza actual</label>
      <label htmlFor={`${id}-piece`}>Pieza y orientación de la corrida</label>
      <select id={`${id}-piece`} className="ng-control" value={selected.mask_ref} onChange={event => { setChoice(event.target.value); setAttempt(0); }}>
        {options.map(item => <option key={item.mask_ref} value={item.mask_ref}>Pedido #{item.piece.id_pedido} · Pieza #{item.piece.id_pieza} · {item.rotation_deg}°</option>)}
      </select>
      {!shown && <p role="status">Consultando máscara de la corrida…</p>}
      {shown?.error && <p role="status">{shown.error} <button type="button" className="ng-button" onClick={() => setAttempt(value => value + 1)}>Reintentar máscara</button></p>}
      {mask && <div data-mask-ref={mask.mask_ref} data-run-id={runId} data-mask-angle={mask.rotation_deg} data-mask-resolution={mask.resolution_mm}>
        <p>Corrida #{runId} · Pieza #{mask.piece.id_pieza} · Giro {mask.rotation_deg}° · Resolución {mask.resolution_mm} mm/celda.</p>
        <p role="status">Ventana exacta: filas {mask.window.row_start + 1}–{mask.window.row_start + mask.window.row_count} de {mask.row_count}; columnas {mask.window.column_start + 1}–{mask.window.column_start + mask.window.column_count} de {mask.columns}.</p>
        <div className="optimization-preview-grid">
          <article className="optimization-preview"><h4>Contorno utilizado completo</h4>
            <GeometryPreview geometry={mask.geometria} pieceId={mask.piece.id_pieza}
              title={`Contorno utilizado de la pieza #${mask.piece.id_pieza}`} frame={getRasterComparisonFrame(mask.geometria)} />
          </article>
          <article className="optimization-preview"><h4>Ventana de la máscara utilizada</h4>
            <RasterPreview raster={raster} pieceId={mask.piece.id_pieza} frame={frame} />
          </article>
        </div>
        <p>Se muestra la ventana indicada, conservando las celdas del cálculo. El resto de la máscara queda fuera de esta vista. La rasterización es una aproximación conservadora.</p>
        {(mask.row_count > 256 || mask.columns > 1024) && <div className="optimization-actions" aria-label="Ventana de la máscara">
          <button className="ng-button" disabled={row === 0} onClick={() => shift(-256, 0)}>Filas anteriores</button>
          <button className="ng-button" disabled={row + mask.window.row_count >= mask.row_count} onClick={() => shift(256, 0)}>Filas siguientes</button>
          <button className="ng-button" disabled={column === 0} onClick={() => shift(0, -1024)}>Columnas anteriores</button>
          <button className="ng-button" disabled={column + mask.window.column_count >= mask.columns} onClick={() => shift(0, 1024)}>Columnas siguientes</button>
        </div>}
        <details><summary>Geometría original del snapshot</summary>
          <GeometryPreview geometry={mask.geometria_original} pieceId={mask.piece.id_pieza} frame={getRasterComparisonFrame(mask.geometria_original)} />
        </details>
      </div>}
    </>}
  </section>;
}
