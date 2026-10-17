import { useId } from 'react';
import { getGeometryBounds } from './visualizationGeometry';

const SHAPE_LABELS = {
  RECTANGULO: 'Rectángulo',
  CIRCUNFERENCIA: 'Circunferencia',
  POLIGONO_CONVEXO: 'Polígono convexo',
};

function geometrySummary(geometry) {
  if (geometry.type === 'RECTANGULO') return `${geometry.width_mm} × ${geometry.height_mm} mm`;
  if (geometry.type === 'CIRCUNFERENCIA') return `Radio: ${geometry.radius_mm} mm`;
  return `${geometry.vertices_mm.length} vértices; coordenadas en mm.`;
}

export function GeometryPreview({ geometry, pieceId, frame }) {
  const id = useId();
  const bounds = getGeometryBounds(geometry);
  if (!bounds || !frame) return <p role="status">La geometría original de esta pieza no está disponible.</p>;

  const label = SHAPE_LABELS[geometry.type] ?? geometry.type;
  const titleId = `geometry-title-${id}`;
  const descriptionId = `geometry-description-${id}`;
  const translation = `translate(${-bounds.minX} ${-bounds.minY})`;
  let shape;
  if (geometry.type === 'RECTANGULO') {
    shape = <rect className="optimization-preview__shape" x="0" y="0" width={geometry.width_mm} height={geometry.height_mm} />;
  } else if (geometry.type === 'CIRCUNFERENCIA') {
    shape = <circle className="optimization-preview__shape" cx="0" cy="0" r={geometry.radius_mm} />;
  } else if (geometry.type === 'POLIGONO_CONVEXO') {
    const points = geometry.vertices_mm.map(([x, y]) => `${x},${y}`).join(' ');
    shape = <polygon className="optimization-preview__shape" points={points} />;
  }

  return <>
    <svg className="optimization-preview__svg" viewBox={frame.viewBox} preserveAspectRatio="xMidYMid meet"
      role="img" aria-labelledby={titleId} aria-describedby={descriptionId}>
      <title id={titleId}>Geometría original de la pieza #{pieceId}</title>
      <desc id={descriptionId}>{label}. {geometrySummary(geometry)} Una geometría.</desc>
      <g transform={translation}>{shape}</g>
    </svg>
    <p className="optimization-preview__caption">{label}: {geometrySummary(geometry)}</p>
    <p className="optimization-preview__legend"><span className="optimization-preview__legend-mark optimization-preview__legend-mark--outline" aria-hidden="true" /> Contorno de la pieza</p>
  </>;
}
