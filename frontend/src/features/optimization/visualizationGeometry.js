const positiveFinite = value => Number.isFinite(value) && value > 0;

export function getGeometryBounds(geometry) {
  if (!geometry || typeof geometry !== 'object') return null;
  if (geometry.type === 'RECTANGULO'
    && positiveFinite(geometry.width_mm) && positiveFinite(geometry.height_mm)) {
    return { minX: 0, minY: 0, width: geometry.width_mm, height: geometry.height_mm };
  }
  if (geometry.type === 'CIRCUNFERENCIA' && positiveFinite(geometry.radius_mm)) {
    const diameter = geometry.radius_mm * 2;
    return { minX: -geometry.radius_mm, minY: -geometry.radius_mm, width: diameter, height: diameter };
  }
  if (geometry.type !== 'POLIGONO_CONVEXO' || !Array.isArray(geometry.vertices_mm)
    || geometry.vertices_mm.length < 3
    || !geometry.vertices_mm.every(point => Array.isArray(point) && point.length === 2 && point.every(Number.isFinite))) return null;

  const xs = geometry.vertices_mm.map(([x]) => x);
  const ys = geometry.vertices_mm.map(([, y]) => y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const width = Math.max(...xs) - minX;
  const height = Math.max(...ys) - minY;
  return positiveFinite(width) && positiveFinite(height) ? { minX, minY, width, height } : null;
}

export function getRasterComparisonFrame(geometry, raster = null) {
  const bounds = getGeometryBounds(geometry);
  if (!bounds) return null;
  const rasterWidth = raster ? raster.columns * raster.resolution_mm : 0;
  const rasterHeight = raster ? raster.row_count * raster.resolution_mm : 0;
  const width = Math.max(bounds.width, rasterWidth);
  const height = Math.max(bounds.height, rasterHeight);
  const padding = Math.max(width, height) * 0.06;
  return {
    bounds,
    width,
    height,
    padding,
    viewBox: `${-padding} ${-padding} ${width + padding * 2} ${height + padding * 2}`,
  };
}

export function* rasterSpanRectangles(spansByRow, cellSize = 1) {
  for (const { row, runs } of spansByRow) {
    for (const [start, endExclusive] of runs) {
      yield {
        x: start * cellSize,
        y: row * cellSize,
        width: (endExclusive - start) * cellSize,
        height: cellSize,
      };
    }
  }
}

export function getRasterDrawLayout(frame, columns, rowCount, width, height, resolutionMm = 1) {
  const fullWidth = frame.width + frame.padding * 2;
  const fullHeight = frame.height + frame.padding * 2;
  const pixelsPerMm = Math.min(width / fullWidth, height / fullHeight);
  const cellSize = pixelsPerMm * resolutionMm;
  const drawnWidth = fullWidth * pixelsPerMm;
  const drawnHeight = fullHeight * pixelsPerMm;
  return {
    cellSize,
    x: (width - drawnWidth) / 2 + frame.padding * pixelsPerMm,
    y: (height - drawnHeight) / 2 + frame.padding * pixelsPerMm,
    maskWidth: columns * cellSize,
    maskHeight: rowCount * cellSize,
  };
}
