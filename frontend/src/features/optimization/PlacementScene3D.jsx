import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { createPlacementScene, clampYaw, DEFAULT_YAW, extrudedSides, projectPoint, projectedPath } from './placementScene';
import './PlacementScene3D.css';
import { ZoomControls } from './InspectionViewport';

const SURFACE = 18;
const PIECE_TOP = 25;
function Dimension({ start, end, label, scene, yaw, camera }) {
  const a = projectPoint(start, SURFACE, scene, yaw, camera), b = projectPoint(end, SURFACE, scene, yaw, camera);
  return <g className="placement-3d-dimension" aria-hidden="true">
    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
    <circle cx={a.x} cy={a.y} r="3" /><circle cx={b.x} cy={b.y} r="3" />
    <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 + 22} textAnchor="middle">{label}</text>
  </g>;
}

export function PlacementScene3D({ snapshot, container, placements, yaw, onYawChange, zoom = 1, onZoomChange = () => {}, camera = { elevation: 48, panX: 0, panY: 0 }, onCameraChange = () => {} }) {
  const id = useId();
  const drag = useRef(null);
  const viewport = useRef(null);
  const [interaction, setInteraction] = useState('orbit');
  useEffect(() => {
    const element = viewport.current;
    if (!element) return undefined;
    const wheel = event => { event.preventDefault(); onZoomChange(Math.max(1, Math.min(4, zoom + (event.deltaY < 0 ? 0.25 : -0.25)))); };
    element.addEventListener('wheel', wheel, { passive: false });
    return () => element.removeEventListener('wheel', wheel);
  }, [zoom, onZoomChange]);
  const moveCamera = changes => onCameraChange({ ...camera, ...changes });
  const reset = () => { onYawChange(DEFAULT_YAW); onZoomChange(1); onCameraChange({ elevation: 48, panX: 0, panY: 0 }); };
  const scene = useMemo(() => createPlacementScene(snapshot, container, placements), [snapshot, container, placements]);
  if (!scene) return <p role="status">No hay geometría válida para mostrar este contenedor en 3D. Consulta la vista 2D.</p>;
  const surfacePath = projectedPath(scene.outline, SURFACE, scene, yaw, camera);
  const pieceDepth = piece => piece.points.reduce((sum, p) => sum + projectPoint(p, PIECE_TOP, scene, yaw, camera).depth, 0) / piece.points.length;
  const sorted = [...scene.pieces].sort((a, b) => pieceDepth(a) - pieceDepth(b));
  const grid = [];
  const origin = projectPoint([0, 0], SURFACE, scene, yaw, camera);
  const axes = [
    ['X', projectPoint([scene.gridStep, 0], SURFACE, scene, yaw, camera), '#c53b37'],
    ['Y', projectPoint([0, scene.gridStep], SURFACE, scene, yaw, camera), '#18784c'],
    ['Z', projectPoint([0, 0], SURFACE + 90, scene, yaw, camera), '#245bb0'],
  ];
  for (let x = scene.gridStep; x < scene.width; x += scene.gridStep) grid.push([[x, 0], [x, scene.height]]);
  for (let y = scene.gridStep; y < scene.height; y += scene.gridStep) grid.push([[0, y], [scene.width, y]]);
  function release(event) {
    if (drag.current?.id !== event.pointerId) return;
    drag.current = null;
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }
  return <section className="placement-3d" aria-label="Vista 3D del resultado">
    <header className="placement-3d-heading"><div><span className="placement-3d-eyebrow">INSPECCIÓN ESPACIAL</span>
      <h3>{container.material_source === 'PLANCHA' ? 'Plancha' : 'Retazo'} #{container.material_id} · unidad {container.stock_unit_index} · {container.material_name}</h3>
      <p>{container.espesor_mm} mm registrados · profundidad visual ilustrativa</p></div>
      <button type="button" className="ng-button" onClick={reset}>Restablecer vista</button>
    </header>
    <p id={`${id}-help`} className="placement-3d-help">Vidrio en XY; Z indica grosor y altura de cámara. Arrastra para orbitar; elige Desplazar para recorrer el corte. Usa la rueda o +/− para acercarte. Flechas: girar; Mayús + flechas: desplazar; RePág/AvPág: elevar/bajar.</p>
    <div className="placement-3d-tools" role="group" aria-label="Cámara del corte">
      <button type="button" className="ng-button" onClick={() => { moveCamera({ elevation: 90, panX: 0, panY: 0 }); onYawChange(0); onZoomChange(1); }}>Vista superior</button>
      <button type="button" className="ng-button" onClick={reset}>Vista en perspectiva</button>
      <button type="button" className="ng-button" onClick={() => { moveCamera({ panX: 0, panY: 0 }); onZoomChange(1); }}>Centrar corte</button>
      <button type="button" className="ng-button" aria-pressed={interaction === 'orbit'} onClick={() => setInteraction('orbit')}>Orbitar</button>
      <button type="button" className="ng-button" aria-pressed={interaction === 'pan'} onClick={() => setInteraction('pan')}>Desplazar</button>
      <label>Altura de cámara (Z)<input type="range" min="5" max="90" value={camera.elevation}
        onChange={event => moveCamera({ elevation: Number(event.target.value) })} /></label>
      <output aria-label="Elevación de cámara">{camera.elevation}° · Z ≈ {Math.round(Math.sin(camera.elevation * Math.PI / 180) * Math.max(scene.width, scene.height) * 2.4)} mm</output>
    </div>
    <ZoomControls label="3D" zoom={zoom} onChange={onZoomChange} />
    <div ref={viewport} className="placement-3d-viewport" role="slider" tabIndex={0} aria-label="Giro horizontal de la vista 3D"
      aria-describedby={`${id}-help`} aria-valuemin={-180} aria-valuemax={180} aria-valuenow={yaw} aria-valuetext={`${yaw} grados`} aria-orientation="horizontal"
      onKeyDown={event => {
        if (event.shiftKey && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
          event.preventDefault();
          moveCamera({ panX: Math.max(-700, Math.min(700, camera.panX + (event.key === 'ArrowRight' ? 40 : event.key === 'ArrowLeft' ? -40 : 0))),
            panY: Math.max(-700, Math.min(700, camera.panY + (event.key === 'ArrowDown' ? 40 : event.key === 'ArrowUp' ? -40 : 0))) });
        } else if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown'].includes(event.key)) {
          event.preventDefault(); moveCamera({ elevation: Math.max(5, Math.min(90, camera.elevation + (['ArrowUp', 'PageUp'].includes(event.key) ? 5 : -5))) });
        } else if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
          event.preventDefault();
          onYawChange(event.key === 'Home' ? -180 : event.key === 'End' ? 180 : clampYaw(yaw + (event.key === 'ArrowRight' ? 5 : -5)));
        }
      }}
      onPointerDown={event => {
        if (event.isPrimary === false || ![0, 2].includes(event.button)) return;
        event.currentTarget.focus({ preventScroll: true });
        drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY, yaw, camera, pan: interaction === 'pan' || event.shiftKey || event.button === 2, width: event.currentTarget.getBoundingClientRect().width || 600 };
        event.currentTarget.setPointerCapture?.(event.pointerId);
      }}
      onPointerMove={event => {
        const start = drag.current;
        if (start?.id !== event.pointerId) return;
        const dx = (event.clientX - start.x) / start.width, dy = (event.clientY - start.y) / start.width;
        if (start.pan) moveCamera({ panX: Math.max(-700, Math.min(700, start.camera.panX + dx * 1600)), panY: Math.max(-700, Math.min(700, start.camera.panY + dy * 1600)) });
        else { onYawChange(clampYaw(Math.round(start.yaw + dx * 360))); moveCamera({ elevation: Math.max(5, Math.min(90, start.camera.elevation + dy * 120)) }); }
      }} onContextMenu={event => event.preventDefault()} onPointerUp={release} onPointerCancel={release} onLostPointerCapture={() => { drag.current = null; }}>
      <svg className="placement-3d-svg" viewBox={scene.viewBox.map(n => n / zoom).join(' ')} aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id={`${id}-glass`} x1="0" y1="0" x2="1" y2="1"><stop stopColor="#f3fbff" /><stop offset="0.55" stopColor="#dceef4" /><stop offset="1" stopColor="#bdd9e4" /></linearGradient>
          <filter id={`${id}-shadow`} x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="15" /></filter>
          <clipPath id={`${id}-surface`}><path d={surfacePath} /></clipPath>
        </defs>
        <path d={projectedPath(scene.outline, -22, scene, yaw, camera)} fill="#25445d" opacity="0.16" filter={`url(#${id}-shadow)`} />
        <g className="placement-3d-sides">{extrudedSides(scene.outline, 0, SURFACE, scene, yaw, camera).map(side =>
          <path key={side.key} d={side.path} fill={side.depth > 0 ? '#6c9fb1' : '#9fc2ce'} />)}</g>
        <path d={surfacePath} fill={`url(#${id}-glass)`} stroke="#6f9caf" strokeWidth="2" />
        <g clipPath={`url(#${id}-surface)`} className="placement-3d-grid">{grid.map(([a, b], i) => {
          const first = projectPoint(a, SURFACE, scene, yaw, camera), last = projectPoint(b, SURFACE, scene, yaw, camera);
          return <line key={i} x1={first.x} y1={first.y} x2={last.x} y2={last.y} />;
        })}</g>
        {sorted.map(piece => {
          const center = piece.points.reduce(([x, y], p) => [x + p[0] / piece.points.length, y + p[1] / piece.points.length], [0, 0]);
          const anchor = projectPoint(center, PIECE_TOP, scene, yaw, camera);
          return <g key={piece.key} data-piece-3d={piece.key}>
            {extrudedSides(piece.points, SURFACE, PIECE_TOP, scene, yaw, camera).map(side => <path key={side.key} d={side.path} fill={piece.edge} />)}
            <path d={projectedPath(piece.points, PIECE_TOP, scene, yaw, camera)} fill={piece.color} stroke={piece.edge} strokeWidth="2" />
            <text className="placement-3d-piece-label" x={anchor.x} y={anchor.y} textAnchor="middle" dominantBaseline="middle">#{piece.placement.id_pieza}</text>
          </g>;
        })}
        <g aria-hidden="true">{axes.map(([label, end, color]) => <g key={label}>
          <line x1={origin.x} y1={origin.y} x2={end.x} y2={end.y} stroke={color} strokeWidth="4" />
          <text x={end.x + 12} y={end.y - 8} fill={color} fontSize="34" fontWeight="700">{label}</text>
        </g>)}</g>
        <Dimension start={[0, scene.height + scene.gridStep / 2]} end={[scene.width, scene.height + scene.gridStep / 2]}
          label={`${scene.width} mm`} scene={scene} yaw={yaw} camera={camera} />
        <Dimension start={[-scene.gridStep / 2, 0]} end={[-scene.gridStep / 2, scene.height]}
          label={`${scene.height} mm`} scene={scene} yaw={yaw} />
      </svg>
      <span className="placement-3d-angle" aria-hidden="true">Z ↑ · giro {yaw}°</span>
    </div>
    <div className="placement-3d-caption"><span>Grilla de referencia · {scene.gridStep} mm</span><span>{scene.pieces.length} piezas en este contenedor</span></div>
    <p className="placement-3d-note">La superficie descubierta representa área libre visual, no retazos reutilizables calculados. Consulta medidas y posiciones precisas en 2D.</p>
    <ul className="placement-3d-legend" aria-label="Piezas en la vista 3D">{scene.pieces.map(piece => <li key={piece.key}>
      <span className="placement-3d-swatch" style={{ backgroundColor: piece.color, borderColor: piece.edge }} aria-hidden="true" />
      <span><strong>Pieza #{piece.placement.id_pieza} · unidad {piece.placement.unit_index}</strong>
        <small>Pedido #{piece.placement.id_pedido} · rotación aplicada: {piece.placement.rotation_deg}°</small></span>
    </li>)}</ul>
    {!scene.pieces.length && <p>No hay piezas colocadas todavía en este contenedor.</p>}
  </section>;
}
