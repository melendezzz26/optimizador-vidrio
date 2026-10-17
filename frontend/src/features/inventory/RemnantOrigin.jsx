import { useEffect, useState } from 'react';
import { getRetazoOrigin } from './inventoryApi';
import { getGeometryBounds } from '../optimization/visualizationGeometry';
import { FeedbackMessage } from '../../shared/components/feedback';

// Inventory serializes Decimal measures as strings. Convert a display copy,
// never the persisted geometry or its precise write payload.
function displayGeometry(raw) {
  if (!raw) return null;
  const number = value => typeof value === 'number' || typeof value === 'string' && value.trim() !== '' ? Number(value) : NaN;
  if (raw.type === 'RECTANGULO') return { ...raw, width_mm: number(raw.width_mm), height_mm: number(raw.height_mm) };
  if (raw.type === 'CIRCUNFERENCIA') return { ...raw, radius_mm: number(raw.radius_mm) };
  return { ...raw, vertices_mm: raw.vertices_mm?.map(point => point.map(number)) };
}

export function RemnantOrigin({ resource, glassName, onOpenCut, canViewCut }) {
  const [state, setState] = useState({ origin: null, error: '' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!resource.id_ejecucion_origen) return undefined;
    const controller = new AbortController();
    getRetazoOrigin(resource.id_retazo, { signal: controller.signal }).then(origin => {
      if (!controller.signal.aborted) setState({ origin, error: '' });
    }).catch(error => { if (!controller.signal.aborted) setState({ origin: null, error: error.message }); });
    return () => controller.abort();
  }, [resource.id_retazo, resource.id_ejecucion_origen, attempt]);
  const geometry = displayGeometry(resource.geometria);
  const bounds = getGeometryBounds(geometry);
  const source = state.origin?.source;
  return <section aria-label="Detalle y origen del retazo" className="remnant-origin">
    <h3>Detalle del retazo</h3>
    <dl className="inventory-history__details">
      <div><dt>Origen</dt><dd>{resource.id_ejecucion_origen ? 'Corte optimizado' : 'Registro manual o histórico'}</dd></div>
      {state.origin?.id_optimizacion && <div><dt>Trabajo/Optimización</dt><dd>#{state.origin.id_optimizacion}</dd></div>}
      {!!state.origin?.order_ids?.length && <div><dt>Pedido(s)</dt><dd>{state.origin.order_ids.map(id => `#${id}`).join(', ')}</dd></div>}
      <div><dt>Fecha de generación / registro</dt><dd>{new Date(resource.fecha_registro).toLocaleString('es-PE')}</dd></div>
      <div><dt>Vidrio y espesor</dt><dd>{glassName ?? `Material #${resource.id_tipo_vidrio}`} · {resource.espesor_mm} mm</dd></div>
      <div><dt>Área</dt><dd>{resource.area_mm2} mm²</dd></div>
      {bounds && <div><dt>Dimensiones exteriores</dt><dd>{bounds.width} × {bounds.height} mm</dd></div>}
      {source && <div><dt>Obtenido de</dt><dd>{source.material_source === 'PLANCHA' ? 'Plancha' : 'Retazo'} #{source.material_id} · unidad {source.stock_unit_index}</dd></div>}
    </dl>
    {state.error && <FeedbackMessage variant="warning">No se pudo consultar el origen. <button type="button" className="ng-button" onClick={() => setAttempt(n => n + 1)}>Reintentar origen</button></FeedbackMessage>}
    {state.origin?.id_optimizacion && canViewCut && onOpenCut && <button className="ng-button" type="button" onClick={() => onOpenCut(state.origin.id_optimizacion)}>Ver corte de origen</button>}
    {bounds ? <figure>
      <svg role="img" aria-label={`Vista previa 2D del retazo ${resource.codigo}`} viewBox={`${bounds.minX - bounds.width * .05} ${bounds.minY - bounds.height * .05} ${bounds.width * 1.1} ${bounds.height * 1.1}`} style={{ width: '100%', height: '240px' }} preserveAspectRatio="xMidYMid meet">
        <g fill="#b9dfd1" stroke="#176f66" strokeWidth={Math.max(bounds.width, bounds.height) / 300}>
          {geometry.type === 'RECTANGULO' ? <rect width={geometry.width_mm} height={geometry.height_mm} />
            : geometry.type === 'CIRCUNFERENCIA' ? <circle r={geometry.radius_mm} />
              : <polygon points={geometry.vertices_mm.map(point => point.join(',')).join(' ')} />}
        </g>
      </svg>
      <figcaption>Geometría registrada · {bounds.width} × {bounds.height} mm. Escala ajustada a la pantalla; las medidas están en milímetros.</figcaption>
    </figure> : <p>La geometría histórica no está disponible para vista previa.</p>}
  </section>;
}
