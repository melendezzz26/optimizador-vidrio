import { useId, useState } from 'react';
import { containerKey, placementKey } from './optimizationModel';
import { getGeometryBounds } from './visualizationGeometry';
import { PlacementScene3D } from './PlacementScene3D';
import { DEFAULT_YAW, placementColors } from './placementScene';
import { placementMatchesGroup } from './materialGroups';
import { InspectionViewport } from './InspectionViewport';
import { RasterInspection } from './RasterInspection';

function Shape({ geometry }) {
  if (geometry.type === 'RECTANGULO') return <rect width={geometry.width_mm} height={geometry.height_mm} />;
  if (geometry.type === 'CIRCUNFERENCIA') return <circle r={geometry.radius_mm} />;
  return <polygon points={geometry.vertices_mm.map(p => p.join(',')).join(' ')} />;
}
export function PlacementCanvas({ snapshot, placements }) {
  const titleId = useId();
  const [chosen, setChosen] = useState('');
  const [chosenGroup, setChosenGroup] = useState('');
  const [view, setView] = useState('2d');
  const [yaw, setYaw] = useState(DEFAULT_YAW);
  const [zoom3d, setZoom3d] = useState(1);
  const group = snapshot.groups.find(g => g.id === chosenGroup) ?? snapshot.groups[0];
  const containers = group?.containers ?? [];
  const container = containers.find(c => containerKey(c) === chosen) ?? containers[0];
  if (!container) return null;
  const compatible = placements.filter(p => p.group_id === group.id && placementMatchesGroup(snapshot, p));
  const visible = compatible.filter(p => containerKey(p) === containerKey(container));
  const bounds = getGeometryBounds(container.geometry);
  const canVisualize = compatible.some(p => containers.some(c => containerKey(c) === containerKey(p)
    && c.material_width_mm > 0 && c.material_height_mm > 0 && getGeometryBounds(c.geometry))
    && getGeometryBounds(p.geometria));
  return <section className="first-fit-canvas" aria-label="Colocaciones First Fit">
    <div className="first-fit-group-select"><label htmlFor={`${titleId}-group`}>Grupo del resultado</label>
      <select id={`${titleId}-group`} className="ng-control" value={group.id} onChange={e => { setChosenGroup(e.target.value); setChosen(''); }}>
        {snapshot.groups.map(g => <option key={g.id} value={g.id}>{g.name} · {g.thickness} mm</option>)}
      </select></div>
    <p>Grupo: {group.name} · {group.thickness} mm · pedidos {group.orders.map(id => `#${id}`).join(', ')}</p>
    <label htmlFor={titleId}>Plancha o retazo</label>
    <select id={titleId} className="ng-control" value={containerKey(container)} onChange={e => setChosen(e.target.value)}>
      {containers.map(c => <option key={containerKey(c)} value={containerKey(c)}>{c.material_source === 'PLANCHA' ? 'Plancha' : 'Retazo'} #{c.material_id} · unidad {c.stock_unit_index} · {c.material_name ?? 'Material'} · {c.espesor_mm} mm</option>)}
    </select>
    <p>{container.material_source === 'PLANCHA' ? 'Plancha seleccionada' : 'Retazo seleccionado'}: {container.material_width_mm} × {container.material_height_mm} mm · unidad física {container.stock_unit_index}</p>
    {canVisualize && <div className="placement-view-switch" role="group" aria-label="Vista del resultado">
      <button type="button" className="ng-button" aria-pressed={view === '2d'} onClick={() => setView('2d')}>Ver en 2D</button>
      <button type="button" className="ng-button" aria-pressed={view === '3d'} onClick={() => setView('3d')}>Ver en 3D</button>
      <button type="button" className="ng-button" aria-pressed={view === 'raster'} onClick={() => setView('raster')}>Ver máscara raster</button>
    </div>}
    {view === 'raster' && canVisualize ? <RasterInspection key={group.id} snapshot={snapshot} group={group} placements={visible} />
      : view === '3d' && canVisualize ? <PlacementScene3D snapshot={snapshot} container={container} placements={visible} yaw={yaw} onYawChange={setYaw} zoom={zoom3d} onZoomChange={setZoom3d} /> : <>
    <InspectionViewport label="2D">
    <svg className="first-fit-sheet" viewBox={`0 0 ${container.material_width_mm} ${container.material_height_mm}`}
      preserveAspectRatio="xMidYMid meet" role="img" aria-label={`Colocaciones en ${container.material_source.toLowerCase()} #${container.material_id}`}>
      <g className="first-fit-container" transform={`translate(${-bounds.minX} ${-bounds.minY})`}><Shape geometry={container.geometry} /></g>
      {visible.map(p => {
        const b = getGeometryBounds(p.geometria);
        const [color, edge] = placementColors(snapshot, p);
        return <g key={placementKey(p)} data-placement={placementKey(p)} className="first-fit-piece" style={{ fill: color, stroke: edge }}
          transform={`translate(${p.x_mm} ${p.y_mm})`}>
          <title>Pedido #{p.id_pedido} · Pieza #{p.id_pieza} · unidad {p.unit_index} · rotación aplicada: {p.rotation_deg}°</title>
          <g transform={`translate(${-b.minX} ${-b.minY})`}><Shape geometry={p.geometria} /></g>
          <text x={b.width / 2} y={b.height / 2} textAnchor="middle" dominantBaseline="middle">#{p.id_pieza}</text>
        </g>;
      })}
    </svg>
    </InspectionViewport>
    <p>Superficie descubierta: área libre visual; no retazos exactos calculados.</p>
    <ul className="first-fit-legend" aria-label="Leyenda de pedidos">{visible.map(p => <li key={placementKey(p)}>
      <span className="first-fit-swatch" style={{ background: placementColors(snapshot, p)[0], border: `1px solid ${placementColors(snapshot, p)[1]}` }} aria-hidden="true" />Pedido #{p.id_pedido} · Pieza #{p.id_pieza} · unidad {p.unit_index}
    </li>)}</ul>
    <ul aria-label="Detalle de colocaciones">{visible.map(p => <li key={placementKey(p)}>Pedido #{p.id_pedido} · Pieza #{p.id_pieza} · unidad {p.unit_index} · rotación aplicada: {p.rotation_deg}°</li>)}</ul>
    {!visible.length && <p>Las piezas aparecerán al recibir sus colocaciones.</p>}
    </>}
  </section>;
}
