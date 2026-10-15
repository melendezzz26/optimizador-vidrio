import { useId, useState } from 'react';
import { containerKey, placementKey } from './optimizationModel';
import { getGeometryBounds } from './visualizationGeometry';
import { PlacementScene3D } from './PlacementScene3D';
import { DEFAULT_YAW } from './placementScene';

function Shape({ geometry }) {
  if (geometry.type === 'RECTANGULO') return <rect width={geometry.width_mm} height={geometry.height_mm} />;
  if (geometry.type === 'CIRCUNFERENCIA') return <circle r={geometry.radius_mm} />;
  return <polygon points={geometry.vertices_mm.map(p => p.join(',')).join(' ')} />;
}
export function PlacementCanvas({ snapshot, placements }) {
  const titleId = useId();
  const [chosen, setChosen] = useState('');
  const [view, setView] = useState('2d');
  const [yaw, setYaw] = useState(DEFAULT_YAW);
  const containers = snapshot.groups.flatMap(g => g.containers);
  const container = containers.find(c => containerKey(c) === chosen) ?? containers[0];
  if (!container) return null;
  const visible = placements.filter(p => containerKey(p) === containerKey(container));
  const bounds = getGeometryBounds(container.geometry);
  const canVisualize = placements.some(p => containers.some(c => containerKey(c) === containerKey(p)
    && c.material_width_mm > 0 && c.material_height_mm > 0 && getGeometryBounds(c.geometry))
    && getGeometryBounds(snapshot.orders.find(o => o.id_pedido === p.id_pedido)?.piezas.find(piece => piece.id_pieza === p.id_pieza)?.geometria));
  return <section className="first-fit-canvas" aria-label="Colocaciones First Fit">
    <label htmlFor={titleId}>Plancha o retazo</label>
    <select id={titleId} className="ng-control" value={containerKey(container)} onChange={e => setChosen(e.target.value)}>
      {containers.map(c => <option key={containerKey(c)} value={containerKey(c)}>{c.material_source === 'plancha' ? 'Plancha' : 'Retazo'} #{c.material_id} · {c.material_name} · {c.espesor_mm} mm</option>)}
    </select>
    <p>{container.material_source === 'plancha' ? 'Plancha seleccionada' : 'Retazo seleccionado'}: {container.material_width_mm} × {container.material_height_mm} mm</p>
    {canVisualize && <div className="placement-view-switch" role="group" aria-label="Vista del resultado">
      <button type="button" className="ng-button" aria-pressed={view === '2d'} onClick={() => setView('2d')}>Ver en 2D</button>
      <button type="button" className="ng-button" aria-pressed={view === '3d'} onClick={() => setView('3d')}>Ver en 3D</button>
    </div>}
    {view === '3d' && canVisualize ? <PlacementScene3D snapshot={snapshot} container={container} placements={placements} yaw={yaw} onYawChange={setYaw} /> : <>
    <svg className="first-fit-sheet" viewBox={`0 0 ${container.material_width_mm} ${container.material_height_mm}`}
      preserveAspectRatio="xMidYMid meet" role="img" aria-label={`Colocaciones en ${container.material_source} #${container.material_id}`}>
      <g className="first-fit-container" transform={`translate(${-bounds.minX} ${-bounds.minY})`}><Shape geometry={container.geometry} /></g>
      {visible.map(p => {
        const piece = snapshot.orders.find(o => o.id_pedido === p.id_pedido).piezas.find(item => item.id_pieza === p.id_pieza);
        const b = getGeometryBounds(piece.geometria);
        const color = snapshot.orders.findIndex(o => o.id_pedido === p.id_pedido) % 2;
        return <g key={placementKey(p)} data-placement={placementKey(p)} className={`first-fit-piece first-fit-piece--${color}`}
          transform={`translate(${p.x_mm} ${p.y_mm}) rotate(${p.rotation_deg}) translate(${-b.minX} ${-b.minY})`}>
          <title>Pedido #{p.id_pedido} · Pieza #{p.id_pieza} · unidad {p.unit_index + 1} · rotación aplicada: {p.rotation_deg}°</title>
          <Shape geometry={piece.geometria} />
          <text x={b.minX + b.width / 2} y={b.minY + b.height / 2} textAnchor="middle" dominantBaseline="middle">#{p.id_pieza}</text>
        </g>;
      })}
    </svg>
    <ul className="first-fit-legend" aria-label="Leyenda de pedidos">{snapshot.orders.map((o, i) => <li key={o.id_pedido}>
      <span className={`first-fit-swatch first-fit-swatch--${i % 2}`} aria-hidden="true" />Pedido #{o.id_pedido}
    </li>)}</ul>
    <ul aria-label="Detalle de colocaciones">{visible.map(p => <li key={placementKey(p)}>Pedido #{p.id_pedido} · Pieza #{p.id_pieza} · unidad {p.unit_index + 1} · rotación aplicada: {p.rotation_deg}°</li>)}</ul>
    {!visible.length && <p>Las piezas aparecerán al recibir sus colocaciones.</p>}
    </>}
  </section>;
}
