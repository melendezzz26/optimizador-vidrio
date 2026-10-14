import { useEffect, useId, useRef } from 'react';
import { drawRasterMask } from './rasterCanvas';

const MAX_VIEWPORT_HEIGHT = 320;
const MAX_DEVICE_PIXEL_RATIO = 2;

export function RasterPreview({ raster, pieceId, frame, rasterizing = false }) {
  const id = useId();
  const canvasRef = useRef(null);
  const viewportRef = useRef(null);
  const titleId = `raster-title-${id}`;
  const descriptionId = `raster-description-${id}`;

  useEffect(() => {
    const canvas = canvasRef.current;
    const viewport = viewportRef.current;
    if (!canvas || !viewport || !raster || !frame) return undefined;

    const draw = () => {
      const bounds = viewport.getBoundingClientRect();
      const width = Math.max(1, bounds.width || 480);
      const height = Math.max(1, Math.min(bounds.height || MAX_VIEWPORT_HEIGHT, MAX_VIEWPORT_HEIGHT));
      const pixelRatio = Math.max(1, Math.min(window.devicePixelRatio || 1, MAX_DEVICE_PIXEL_RATIO));
      canvas.width = Math.ceil(width * pixelRatio);
      canvas.height = Math.ceil(height * pixelRatio);
      const context = canvas.getContext('2d');
      if (!context) return;
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      const styles = window.getComputedStyle(canvas);
      const color = (name, fallback) => styles.getPropertyValue(name).trim() || fallback;
      drawRasterMask(context, raster, frame, { width, height }, {
        background: color('--ng-surface', '#ffffff'),
        occupied: color('--ng-primary-action', '#2563eb'),
        grid: color('--ng-border-strong', '#64748b'),
      });
    };

    draw();
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(draw) : null;
    observer?.observe(viewport);
    window.addEventListener('resize', draw);
    return () => {
      observer?.disconnect();
      window.removeEventListener('resize', draw);
    };
  }, [frame, raster]);

  if (!raster || !frame) return <p className="optimization-preview__empty" role="status">
    {rasterizing ? 'Rasterizando la pieza seleccionada...' : 'Rasteriza la pieza seleccionada para visualizar su máscara.'}
  </p>;

  const title = `Máscara raster de la pieza #${pieceId}`;
  const description = `${raster.tipo_forma}; resolución ${raster.resolution_mm} mm por celda; ${raster.row_count} filas, ${raster.columns} columnas, ${raster.occupied_cells} celdas ocupadas; cantidad ${raster.cantidad}.`;
  return <>
    <div className="optimization-preview__canvas-viewport" ref={viewportRef}>
      <canvas ref={canvasRef} role="img" aria-labelledby={titleId} aria-describedby={descriptionId}>
        La máscara contiene {raster.occupied_cells} celdas ocupadas.
      </canvas>
    </div>
    <p id={descriptionId} className="optimization-preview__caption">{description}</p>
    <p className="optimization-preview__legend"><span className="optimization-preview__legend-mark optimization-preview__legend-mark--occupied" aria-hidden="true" /> Celda ocupada; las celdas sin relleno están vacías.</p>
    <span id={titleId} className="optimization-preview__accessible-title">{title}</span>
  </>;
}
