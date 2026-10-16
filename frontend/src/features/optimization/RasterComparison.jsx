import { useId, useMemo } from 'react';
import { GeometryPreview } from './GeometryPreview';
import { RasterPreview } from './RasterPreview';
import { getRasterComparisonFrame } from './visualizationGeometry';

export function RasterComparison({ geometry, raster, piece, rasterizing = false }) {
  const id = useId();
  const frame = useMemo(() => getRasterComparisonFrame(geometry, raster), [geometry, raster]);
  if (!piece || !frame) return null;

  return <section className="optimization-comparison" aria-labelledby={`${id}-comparison-title`}>
    <h3 id={`${id}-comparison-title`}>Geometría original y máscara raster</h3>
    <p>Las vistas conservan la misma escala física. La extensión de la rejilla puede exceder el contorno por el redondeo del raster.</p>
    <div className="optimization-preview-grid">
      <article className="optimization-preview" aria-labelledby={`${id}-geometry-title`}>
        <h4 id={`${id}-geometry-title`}>Geometría original</h4>
        <GeometryPreview geometry={geometry} pieceId={piece.id_pieza} frame={frame} />
      </article>
      <article className="optimization-preview" aria-labelledby={`${id}-mask-title`}>
        <h4 id={`${id}-mask-title`}>Máscara raster</h4>
        <RasterPreview raster={raster} pieceId={piece.id_pieza} frame={frame} rasterizing={rasterizing} />
      </article>
    </div>
  </section>;
}
