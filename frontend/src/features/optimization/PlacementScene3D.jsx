import { useId, useMemo, useRef } from 'react';
import { createPlacementScene, clampYaw, DEFAULT_YAW, extrudedSides, projectPoint, projectedPath } from './placementScene';
import './PlacementScene3D.css';
import { ZoomControls } from './InspectionViewport';

const SURFACE = 18;
const PIECE_TOP = 25;
function Dimension({ start, end, label, scene, yaw }) {
  const a = projectPoint(start, SURFACE, scene, yaw), b = projectPoint(end, SURFACE, scene, yaw);
  return <g className="placement-3d-dimension" aria-hidden="true">
    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
    <circle cx={a.x} cy={a.y} r="3" /><circle cx={b.x} cy={b.y} r="3" />
    <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 + 22} textAnchor="middle">{label}</text>
  </g>;
}

export function PlacementScene3D({ snapshot, container, placements, yaw, onYawChange, zoom = 1, onZoomChange = () => {} }) {
  const id = useId();
  const drag = useRef(null);
  const scene = useMemo(() => createPlacementScene(snapshot, container, placements), [snapshot, container, placements]);
  if (!scene) return <p role="status">No hay geometría válida para mostrar este contenedor en 3D. Consulta la vista 2D.</p>;
  const surfacePath = projectedPath(scene.outline, SURFACE, scene, yaw);
  const pieceDepth = piece => piece.points.reduce((sum, p) => sum + projectPoint(p, PIECE_TOP, scene, yaw).depth, 0) / piece.points.length;
  const sorted = [...scene.pieces].sort((a, b) => pieceDepth(a) - pieceDepth(b));
  const grid = [];
  for (let x = scene.gridStep; x < scene.width; x += scene.gridStep) grid.push([[x, 0], [x, scene.height]]);
  for (let y = scene.gridStep; y < scene.height; y += scene.gridStep) grid.push([[0, y], [scene.width, y]]);
  function release(event) {
    if (drag.current?.id !== event.pointerId) return;
    drag.current = null;
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }
  return <section className="placement-3d" aria-label="Vista 3D del resultado">
    <header className="placement-3d-heading"><div><span className="placement-3d-eyebrow">INSPECCIÓN ESPACIAL</span>
      <h3>{container.material_source === 'plancha' ? 'Plancha' : 'Retazo'} #{container.material_id} · {container.material_name}</h3>
      <p>{container.espesor_mm} mm registrados · profundidad visual ilustrativa</p></div>
      <button type="button" className="ng-button" onClick={() => { onYawChange(DEFAULT_YAW); onZoomChange(1); }}>Restablecer vista</button>
    </header>
    <p id={`${id}-help`} className="placement-3d-help">Arrastra horizontalmente o usa las flechas ← →. Giro limitado a −90° / +90°; inclinación fija.</p>
    <ZoomControls label="3D" zoom={zoom} onChange={onZoomChange} />
    <div className="placement-3d-viewport" role="slider" tabIndex={0} aria-label="Giro horizontal de la vista 3D"
      aria-describedby={`${id}-help`} aria-valuemin={-90} aria-valuemax={90} aria-valuenow={yaw} aria-valuetext={`${yaw} grados`} aria-orientation="horizontal"
      onKeyDown={event => {
        if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
          event.preventDefault();
          onYawChange(event.key === 'Home' ? -90 : event.key === 'End' ? 90 : clampYaw(yaw + (event.key === 'ArrowRight' ? 5 : -5)));
        }
      }}
      onPointerDown={event => {
        if (event.isPrimary === false || event.button !== 0) return;
        event.currentTarget.focus({ preventScroll: true });
        drag.current = { id: event.pointerId, x: event.clientX, yaw, width: event.currentTarget.getBoundingClientRect().width || 600 };
        event.currentTarget.setPointerCapture?.(event.pointerId);
      }}
      onPointerMove={event => {
        const start = drag.current;
        if (start?.id === event.pointerId) onYawChange(clampYaw(Math.round(start.yaw + (event.clientX - start.x) / start.width * 180)));
      }} onPointerUp={release} onPointerCancel={release} onLostPointerCapture={() => { drag.current = null; }}>
      <svg className="placement-3d-svg" viewBox={scene.viewBox.map(n => n / zoom).join(' ')} aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id={`${id}-glass`} x1="0" y1="0" x2="1" y2="1"><stop stopColor="#f3fbff" /><stop offset="0.55" stopColor="#dceef4" /><stop offset="1" stopColor="#bdd9e4" /></linearGradient>
          <filter id={`${id}-shadow`} x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="15" /></filter>
          <clipPath id={`${id}-surface`}><path d={surfacePath} /></clipPath>
        </defs>
        <path d={projectedPath(scene.outline, -22, scene, yaw)} fill="#25445d" opacity="0.16" filter={`url(#${id}-shadow)`} />
        <g className="placement-3d-sides">{extrudedSides(scene.outline, 0, SURFACE, scene, yaw).map(side =>
          <path key={side.key} d={side.path} fill={side.depth > 0 ? '#6c9fb1' : '#9fc2ce'} />)}</g>
        <path d={surfacePath} fill={`url(#${id}-glass)`} stroke="#6f9caf" strokeWidth="2" />
        <g clipPath={`url(#${id}-surface)`} className="placement-3d-grid">{grid.map(([a, b], i) => {
          const first = projectPoint(a, SURFACE, scene, yaw), last = projectPoint(b, SURFACE, scene, yaw);
          return <line key={i} x1={first.x} y1={first.y} x2={last.x} y2={last.y} />;
        })}</g>
        {sorted.map(piece => {
          const center = piece.points.reduce(([x, y], p) => [x + p[0] / piece.points.length, y + p[1] / piece.points.length], [0, 0]);
          const anchor = projectPoint(center, PIECE_TOP, scene, yaw);
          return <g key={piece.key} data-piece-3d={piece.key}>
            {extrudedSides(piece.points, SURFACE, PIECE_TOP, scene, yaw).map(side => <path key={side.key} d={side.path} fill={piece.edge} />)}
            <path d={projectedPath(piece.points, PIECE_TOP, scene, yaw)} fill={piece.color} stroke={piece.edge} strokeWidth="2" />
            <text className="placement-3d-piece-label" x={anchor.x} y={anchor.y} textAnchor="middle" dominantBaseline="middle">#{piece.placement.id_pieza}</text>
          </g>;
        })}
        <Dimension start={[0, scene.height + scene.gridStep / 2]} end={[scene.width, scene.height + scene.gridStep / 2]}
          label={`${scene.width} mm`} scene={scene} yaw={yaw} />
        <Dimension start={[-scene.gridStep / 2, 0]} end={[-scene.gridStep / 2, scene.height]}
          label={`${scene.height} mm`} scene={scene} yaw={yaw} />
      </svg>
      <span className="placement-3d-angle" aria-hidden="true">Y · {yaw}°</span>
    </div>
    <div className="placement-3d-caption"><span>Grilla de referencia · {scene.gridStep} mm</span><span>{scene.pieces.length} piezas en este contenedor</span></div>
    <p className="placement-3d-note">La superficie descubierta representa área libre visual, no retazos reutilizables calculados. Consulta medidas y posiciones precisas en 2D.</p>
    <ul className="placement-3d-legend" aria-label="Piezas en la vista 3D">{scene.pieces.map(piece => <li key={piece.key}>
      <span className="placement-3d-swatch" style={{ backgroundColor: piece.color, borderColor: piece.edge }} aria-hidden="true" />
      <span><strong>Pieza #{piece.placement.id_pieza} · unidad {piece.placement.unit_index + 1}</strong>
        <small>Pedido #{piece.placement.id_pedido} · rotación aplicada: {piece.placement.rotation_deg}°</small></span>
    </li>)}</ul>
    {!scene.pieces.length && <p>No hay piezas colocadas todavía en este contenedor.</p>}
  </section>;
}
