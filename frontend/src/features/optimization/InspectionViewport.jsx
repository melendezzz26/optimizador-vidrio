import { useRef, useState } from 'react';
import './InspectionViewport.css';

export function ZoomControls({ zoom, onChange, label }) {
  return <div className="inspection-controls" role="group" aria-label={`Zoom ${label}`}>
    <button className="ng-button" type="button" aria-label={`Alejar ${label}`} disabled={zoom <= 1} onClick={() => onChange(Math.max(1, zoom - 0.5))}>−</button>
    <output aria-label={`Ampliación ${label}`}>{Math.round(zoom * 100)} %</output>
    <button className="ng-button" type="button" aria-label={`Acercar ${label}`} disabled={zoom >= 4} onClick={() => onChange(Math.min(4, zoom + 0.5))}>+</button>
    <button className="ng-button" type="button" onClick={() => onChange(1)}>Ajustar {label}</button>
  </div>;
}

export function InspectionViewport({ label, children }) {
  const [zoom, setZoom] = useState(1);
  const scroll = useRef(null);
  return <>
    <ZoomControls label={label} zoom={zoom} onChange={value => {
      setZoom(value);
      if (value === 1 && scroll.current) { scroll.current.scrollLeft = 0; scroll.current.scrollTop = 0; }
    }} />
    <div className="inspection-scroll" ref={scroll} tabIndex={0} role="region" aria-label={`Inspección ampliada ${label}`}>
      <div className="inspection-content" style={{ width: `${zoom * 100}%`, '--inspection-zoom': zoom }}>{children}</div>
    </div>
    <p className="inspection-help">Amplía con + y −. Desplaza la vista ampliada con las barras, gesto táctil o flechas al enfocar el panel.</p>
  </>;
}
